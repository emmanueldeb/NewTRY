// =============================================================================
// TRY_TickSequenceExport_v4.cpp
//
// Evolution de v2. Ajoute deux nouveaux criteres de coupure de sequence en
// plus du changement de sens d'agression :
//
//   - PAUSE   : silence intra-session entre deux prints same-side superieur
//               a MaxPauseUS (microsecondes). Defaut 1, soit "coupure des
//               qu'il y a un changement de microseconde". Cible l'unite
//               atomique d'agression (un seul ordre marche balayant plusieurs
//               offres dans la meme microseconde).
//   - SESSION : changement de trading day (via sc.GetTradingDayDate). Evite
//               qu'une sequence ne chevauche une fermeture de marche.
//
// La cause de coupure est exportee dans la colonne CutReason :
//   - SIDE    : la print suivante est de sens oppose.
//   - PAUSE   : gap > MaxPauseUS sans print same-side.
//   - SESSION : changement de trading day.
//   - EOF     : derniere sequence en cours a la fin de l'export.
//
// Priorite : SESSION > SIDE > PAUSE.
//
// Precision interne : v2 utilisait AsMillisecondsSinceBaseDate (1 ms). v4
// utilise AsMicrosecondsSinceBaseDate (1 us, exposee par SCDateTime). Les
// colonnes durees sont basculees en microsecondes :
//   - DurationMS  -> DurationUS
//   - GapMsBefore -> GapUsBefore
//
// Nouvelle colonne CutReason inseree juste avant VolProfile.
//
// Sortie CSV : C:\SierraChart\Data\TRY_TickSequenceExport_SYMBOL_SUFFIX.csv
// Suffixe par defaut : TICKSEQ_V4.
//
// Sierra Chart compile cette study. Ne pas compiler avec Codex.
// Version : 4
// =============================================================================

#include "sierrachart.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <vector>

SCDLLName("TRY Tick Sequence Export v4")

static void TRYSeq4AppendText(SCStudyInterfaceRef sc, int fileHandle, const SCString& text)
{
    unsigned int bytesWritten = 0;
    sc.WriteFile(fileHandle, text.GetChars(), (int)std::strlen(text.GetChars()), &bytesWritten);
}

static SCString TRYSeq4SanitizedSymbol(const SCString& text)
{
    SCString out;
    const char* chars = text.GetChars();
    for (int i = 0; chars != NULL && chars[i] != '\0'; ++i)
    {
        const char c = chars[i];
        const bool unsafe =
            c == '/' || c == '\\' || c == ':' || c == '*' || c == '?'
            || c == '"' || c == '<' || c == '>' || c == '|' || c == ' ';
        out.AppendFormat("%c", unsafe ? '_' : c);
    }
    return out;
}

static const char* TRYSeq4SideText(int side)
{
    if (side > 0)
        return "BUY";
    if (side < 0)
        return "SELL";
    return "UNKNOWN";
}

static int TRYSeq4AggressionSide(SCStudyInterfaceRef sc, int barIndex)
{
    const float askVolume = sc.AskVolume[barIndex];
    const float bidVolume = sc.BidVolume[barIndex];

    if (askVolume > bidVolume && askVolume > 0.0f)
        return 1;
    if (bidVolume > askVolume && bidVolume > 0.0f)
        return -1;
    if (askVolume > 0.0f && bidVolume <= 0.0f)
        return 1;
    if (bidVolume > 0.0f && askVolume <= 0.0f)
        return -1;

    return 0;
}

static long long TRYSeq4MicrosOf(const SCDateTime& dt)
{
    return (long long)dt.AsMicrosecondsSinceBaseDate();
}

struct TRYSeq4State
{
    bool active;
    int side;
    int prints;
    int volume;
    double priceVolume;
    double priceStart;
    double priceEnd;
    double priceMin;
    double priceMax;
    SCDateTime startDT;
    SCDateTime endDT;
    long long startUS;
    long long endUS;
    int startBarIndex;
    int endBarIndex;
    std::vector<int> volProfile;
    double tickSize;
    int tradingDay;

    TRYSeq4State() { Reset(); }

    void Reset()
    {
        active = false;
        side = 0;
        prints = 0;
        volume = 0;
        priceVolume = 0.0;
        priceStart = 0.0;
        priceEnd = 0.0;
        priceMin = 0.0;
        priceMax = 0.0;
        startDT = SCDateTime(0.0);
        endDT = SCDateTime(0.0);
        startUS = 0;
        endUS = 0;
        startBarIndex = -1;
        endBarIndex = -1;
        volProfile.clear();
        tickSize = 0.0;
        tradingDay = -1;
    }

    int OffsetFromMin(double price) const
    {
        if (tickSize <= 0.0)
            return 0;
        return (int)std::floor((price - priceMin) / tickSize + 0.5);
    }

    void Start(const SCDateTime& dt, long long us, double price, int inVolume, int inSide, int barIndex, double ts, int td)
    {
        Reset();
        active = true;
        side = inSide;
        prints = 1;
        volume = inVolume;
        priceVolume = price * (double)inVolume;
        priceStart = price;
        priceEnd = price;
        priceMin = price;
        priceMax = price;
        startDT = dt;
        endDT = dt;
        startUS = us;
        endUS = us;
        startBarIndex = barIndex;
        endBarIndex = barIndex;
        tickSize = ts;
        tradingDay = td;
        volProfile.assign(1, inVolume);
    }

    void Add(const SCDateTime& dt, long long us, double price, int inVolume, int barIndex)
    {
        prints++;
        volume += inVolume;
        priceVolume += price * (double)inVolume;
        priceEnd = price;
        endDT = dt;
        endUS = us;
        endBarIndex = barIndex;

        if (tickSize <= 0.0)
            return;

        if (price < priceMin)
        {
            const int extraSlots = (int)std::floor((priceMin - price) / tickSize + 0.5);
            if (extraSlots > 0)
                volProfile.insert(volProfile.begin(), (size_t)extraSlots, 0);
            priceMin = price;
        }
        else if (price > priceMax)
        {
            const int extraSlots = (int)std::floor((price - priceMax) / tickSize + 0.5);
            if (extraSlots > 0)
                volProfile.insert(volProfile.end(), (size_t)extraSlots, 0);
            priceMax = price;
        }

        const int offset = OffsetFromMin(price);
        if (offset >= 0 && offset < (int)volProfile.size())
            volProfile[offset] += inVolume;
    }
};

static void TRYSeq4SerializeProfile(const std::vector<int>& profile, SCString& out)
{
    out = "";
    for (size_t i = 0; i < profile.size(); ++i)
    {
        if (i > 0)
            out += ";";
        out.AppendFormat("%d", profile[i]);
    }
}

static void TRYSeq4Write(SCStudyInterfaceRef sc, int fileHandle, SCString& row, SCString& vpBuf, const TRYSeq4State& s, long long prevEndUS, const char* cutReason)
{
    const double vwap = s.volume > 0 ? s.priceVolume / (double)s.volume : s.priceStart;
    const long long gapBefore = prevEndUS < 0 ? -1LL : (s.startUS - prevEndUS);
    const long long durationUS = s.endUS - s.startUS;

    TRYSeq4SerializeProfile(s.volProfile, vpBuf);

    row.Format(
        "%s,%s,%s,%s,%d,%d,%lld,%lld,%.8f,%.8f,%.8f,%.8f,%.8f,%d,%d,%.8f,%s,%s\r\n",
        sc.FormatDateTimeMS(s.startDT).GetChars(),
        sc.FormatDateTimeMS(s.endDT).GetChars(),
        sc.Symbol.GetChars(),
        TRYSeq4SideText(s.side),
        s.prints,
        s.volume,
        durationUS,
        gapBefore,
        s.priceStart,
        s.priceEnd,
        s.priceMin,
        s.priceMax,
        vwap,
        s.startBarIndex,
        s.endBarIndex,
        s.tickSize,
        cutReason,
        vpBuf.GetChars());
    TRYSeq4AppendText(sc, fileHandle, row);
}

SCSFExport scsf_TRY_TickSequenceExport_v4(SCStudyInterfaceRef sc)
{
    SCInputRef In_OutputSuffix = sc.Input[0];
    SCInputRef In_ExportOnlyClosedBars = sc.Input[1];
    SCInputRef In_ExportOnFullRecalcOnly = sc.Input[2];
    SCInputRef In_MaxDaysToExport = sc.Input[3];
    SCInputRef In_WarnIfNotOneTradeChart = sc.Input[4];
    SCInputRef In_MaxPauseUS = sc.Input[5];

    if (sc.SetDefaults)
    {
        sc.GraphName = "TRY Tick Sequence Export v4";
        sc.StudyDescription =
            "Export CSV des sequences consecutives same-side. Coupures: SIDE "
            "(changement de sens), PAUSE (gap > MaxPauseUS), SESSION (changement "
            "de trading day). Defaut MaxPauseUS=1 us = unite atomique d'agression. "
            "A utiliser sur chart Number of Trades Per Bar = 1.";
        sc.GraphRegion = 0;
        sc.AutoLoop = 0;
        sc.MaintainVolumeAtPriceData = 0;

        In_OutputSuffix.Name = "CSV Output Suffix";
        In_OutputSuffix.SetString("TICKSEQ_V4");

        In_ExportOnlyClosedBars.Name = "Export Only Closed Bars";
        In_ExportOnlyClosedBars.SetYesNo(1);

        In_ExportOnFullRecalcOnly.Name = "Export On Full Recalculation Only";
        In_ExportOnFullRecalcOnly.SetYesNo(1);

        In_MaxDaysToExport.Name = "Max Days To Export (0 = all)";
        In_MaxDaysToExport.SetInt(24);
        In_MaxDaysToExport.SetIntLimits(0, 10000);

        In_WarnIfNotOneTradeChart.Name = "Warn If Chart Does Not Look Like 1-Trade Bars";
        In_WarnIfNotOneTradeChart.SetYesNo(1);

        In_MaxPauseUS.Name = "Max Pause Between Same-Side Prints (us)";
        In_MaxPauseUS.SetInt(1);
        In_MaxPauseUS.SetIntLimits(0, 1000000000);  // 0 a 1000 s (~16 min)

        return;
    }

    if (In_ExportOnFullRecalcOnly.GetYesNo() && !sc.IsFullRecalculation)
        return;

    if (sc.ArraySize <= 0)
        return;

    const int lastIndexToExport = In_ExportOnlyClosedBars.GetYesNo()
        ? sc.ArraySize - 2
        : sc.ArraySize - 1;

    if (lastIndexToExport < 0)
    {
        sc.AddMessageToLog("TRY_TickSequenceExport_v4: historique insuffisant.", 1);
        return;
    }

    const int maxDays = In_MaxDaysToExport.GetInt();
    const double tickSize = sc.TickSize;
    const long long maxPauseUS = (long long)In_MaxPauseUS.GetInt();

    if (tickSize <= 0.0)
    {
        sc.AddMessageToLog("TRY_TickSequenceExport_v4: TickSize <= 0, abandon.", 1);
        return;
    }

    SCString suffix = In_OutputSuffix.GetString();
    if (suffix.IsEmpty())
        suffix = "TICKSEQ_V4";

    SCString path = sc.DataFilesFolder();
    path += "\\TRY_TickSequenceExport_";
    path += TRYSeq4SanitizedSymbol(sc.Symbol).GetChars();
    path += "_";
    path += TRYSeq4SanitizedSymbol(suffix).GetChars();
    path += ".csv";

    int fileHandle = 0;
    if (sc.OpenFile(path, n_ACSIL::FILE_MODE_OPEN_TO_REWRITE_FROM_START, fileHandle) == 0)
    {
        SCString msg;
        msg.Format("TRY_TickSequenceExport_v4: impossible d'ouvrir le CSV: %s", path.GetChars());
        sc.AddMessageToLog(msg, 1);
        return;
    }

    SCString header =
        "StartDateTime,EndDateTime,Symbol,Side,Prints,Volume,DurationUS,GapUsBefore,"
        "PriceStart,PriceEnd,PriceMin,PriceMax,VWAP,StartBarIndex,EndBarIndex,"
        "TickSize,CutReason,VolProfile\r\n";
    TRYSeq4AppendText(sc, fileHandle, header);

    SCDateTime firstDT(0.0);
    bool firstDTSet = false;
    int barsWithMoreThanOneTrade = 0;
    int seqWritten = 0;
    int ticksConsumed = 0;
    bool maxDaysReached = false;
    SCString row;
    SCString vpBuf;

    TRYSeq4State state;
    long long prevEndUS = -1;

    int cutCountSide = 0;
    int cutCountPause = 0;
    int cutCountSession = 0;

    for (int barIndex = 0; barIndex <= lastIndexToExport; ++barIndex)
    {
        const int numberOfTrades = (int)sc.NumberOfTrades[barIndex];
        if (numberOfTrades > 1)
            barsWithMoreThanOneTrade++;

        const int volume = (int)sc.Volume[barIndex];
        if (volume <= 0)
            continue;

        const SCDateTime dt = sc.BaseDateTimeIn[barIndex];

        if (!firstDTSet)
        {
            firstDT = dt;
            firstDTSet = true;
        }

        if (maxDays > 0)
        {
            const double daysSinceStart = dt.GetAsDouble() - firstDT.GetAsDouble();
            if (daysSinceStart > (double)maxDays)
            {
                maxDaysReached = true;
                break;
            }
        }

        const double price = sc.Close[barIndex];
        const int side = TRYSeq4AggressionSide(sc, barIndex);
        const long long nowUS = TRYSeq4MicrosOf(dt);
        const int nowTradingDay = sc.GetTradingDayDate(dt);

        ticksConsumed++;

        if (!state.active)
        {
            state.Start(dt, nowUS, price, volume, side, barIndex, tickSize, nowTradingDay);
            continue;
        }

        // Priorite des causes de coupure : SESSION > SIDE > PAUSE.
        const bool sessionBreak = (nowTradingDay != state.tradingDay);
        const bool sideBreak = (side != state.side);
        const bool pauseBreak = ((nowUS - state.endUS) > maxPauseUS);

        const char* cutReason = NULL;
        if (sessionBreak)
            cutReason = "SESSION";
        else if (sideBreak)
            cutReason = "SIDE";
        else if (pauseBreak)
            cutReason = "PAUSE";

        if (cutReason != NULL)
        {
            TRYSeq4Write(sc, fileHandle, row, vpBuf, state, prevEndUS, cutReason);
            seqWritten++;
            if (sessionBreak) cutCountSession++;
            else if (sideBreak) cutCountSide++;
            else cutCountPause++;
            prevEndUS = state.endUS;
            state.Start(dt, nowUS, price, volume, side, barIndex, tickSize, nowTradingDay);
        }
        else
        {
            state.Add(dt, nowUS, price, volume, barIndex);
        }
    }

    if (state.active)
    {
        TRYSeq4Write(sc, fileHandle, row, vpBuf, state, prevEndUS, "EOF");
        seqWritten++;
    }

    sc.CloseFile(fileHandle);

    if (In_WarnIfNotOneTradeChart.GetYesNo() && barsWithMoreThanOneTrade > 0)
    {
        SCString warn;
        warn.Format(
            "TRY_TickSequenceExport_v4: %d barres ont NumberOfTrades > 1. "
            "Pour un export sequence propre, utiliser un chart Number of Trades Per Bar = 1.",
            barsWithMoreThanOneTrade);
        sc.AddMessageToLog(warn, 1);
    }

    SCString msg;
    msg.Format(
        "TRY_TickSequenceExport_v4: CSV exporte (%d sequences sur %d ticks, "
        "coupures SIDE=%d PAUSE=%d SESSION=%d%s): %s",
        seqWritten,
        ticksConsumed,
        cutCountSide,
        cutCountPause,
        cutCountSession,
        maxDaysReached ? ", borne MaxDays atteinte" : "",
        path.GetChars());
    sc.AddMessageToLog(msg, 0);
}
