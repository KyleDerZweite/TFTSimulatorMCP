import {
  BarChart,
  Callout,
  Divider,
  Grid,
  H1,
  H2,
  Stack,
  Stat,
  Table,
  Text,
} from "cursor/canvas";

const DEATH_ROUNDS = [
  "4", "5", "6", "7", "8", "9", "10", "11", "12", "13",
  "14", "15", "16", "17", "18", "19", "20", "21", "22", "23",
  "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
  "34", "35", "36", "37", "38", "39", "40",
];

const DEATH_COUNTS = [
  3, 1, 6, 24, 3, 1, 2, 5, 73, 113,
  112, 0, 104, 18, 26, 38, 39, 1, 12, 41,
  9, 12, 50, 1, 47, 38, 45, 29, 37, 0,
  23, 27, 24, 14, 10, 0, 6,
];

export default function DefaultAgentSinglePlayer() {
  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Default agent, single-player campaign</H1>
        <Text tone="secondary">
          1,000 games of Default_Agent on TFT_Single_Player_Simulator, seeds
          0 through 999. Simulator revision a197a2a5. Each planning phase
          allows 15 actions. A loss ends the run, so the death round is how
          far that game went. The campaign is 46 rounds; round 1 is the
          opening carousel and minions, played before the agent acts.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="19" label="Median death round" />
        <Stat value="21.0" label="Mean death round" />
        <Stat value="4–40" label="Earliest to latest death" />
        <Stat value="0 / 1,000" label="Campaigns cleared" tone="warning" />
      </Grid>

      <Callout tone="warning" title="Six games were still winning at round 40">
        Those six won round 40. The next observation then failed the
        encoder check `game_round &lt; 40`, so the campaign could not
        continue. They are not losses and they are not clears. The death
        chart leaves them out. The reach table counts them as alive through
        round 40.
      </Callout>

      <Callout tone="info" title="Health does not decide these games">
        All 1,000 games still had 100 health at the end. This environment
        scores each fight as a win or a loss and stops on the first loss.
        It does not apply stage damage.
      </Callout>

      <H2>Games lost on each campaign round</H2>
      <BarChart
        categories={DEATH_ROUNDS}
        series={[{ name: "Games lost", data: DEATH_COUNTS, tone: "danger" }]}
        height={240}
        yMax={130}
        beginAtZero
      />
      <Text size="small" tone="tertiary">
        Losing round, 1-based, out of 46. 994 losses. Rounds with no bar had
        no deaths. The tallest bars are round 13 (113 games) and round 14
        (112). Source: local simulator, seeds 0–999, 18 Oct 2026.
      </Text>

      <Grid columns={2} gap={24}>
        <Stack gap={8}>
          <H2>How many games reached each round</H2>
          <Table
            headers={["Round", "Games still alive", "Share"]}
            columnAlign={["right", "right", "right"]}
            rows={[
              ["10", "962", "96.2%"],
              ["15", "657", "65.7%"],
              ["20", "471", "47.1%"],
              ["25", "369", "36.9%"],
              ["30", "221", "22.1%"],
              ["35", "87", "8.7%"],
              ["40", "12", "1.2%"],
              ["46 (cleared)", "0", "0%"],
            ]}
            rowTone={[
              undefined,
              undefined,
              undefined,
              undefined,
              "warning",
              "warning",
              "danger",
              "danger",
            ]}
          />
          <Text size="small" tone="tertiary">
            A game reached a round if it lost on that round or later, or if
            it was one of the six still winning when the encoder stopped.
            Half the field is gone by round 20.
          </Text>
        </Stack>
        <Stack gap={8}>
          <H2>What ended the game</H2>
          <Table
            headers={["Ending", "Games", "Round range"]}
            columnAlign={["left", "right", "right"]}
            rows={[
              ["Generated opponent", "761", "4–40"],
              ["Carousel, then opponent", "230", "7–40"],
              ["Minions", "3", "9–27"],
              ["Encoder stop, still winning", "6", "40"],
            ]}
            rowTone={["danger", "warning", "neutral", "info"]}
          />
          <Text size="small" tone="tertiary">
            991 of 994 losses were fights against a generated board. Three
            games lost a minion round.
          </Text>
        </Stack>
      </Grid>

      <Divider />

      <H2>Board level when the game ended</H2>
      <Grid columns={2} gap={24}>
        <Stack gap={8}>
          <Text weight="semibold">Agent level</Text>
          <Table
            headers={["Level", "Games", "Share"]}
            columnAlign={["right", "right", "right"]}
            rows={[
              ["3", "3", "0.3%"],
              ["4", "31", "3.1%"],
              ["5", "135", "13.5%"],
              ["6", "215", "21.5%"],
              ["7", "170", "17.0%"],
              ["8", "446", "44.6%"],
            ]}
          />
          <Text size="small" tone="tertiary">
            Median 7, mean 6.86. No game reached level 9. Level 8 is the
            common end state (446 games).
          </Text>
        </Stack>
        <Stack gap={8}>
          <Text weight="semibold">Opponent board level</Text>
          <Table
            headers={["Level", "Games", "Share of losses"]}
            columnAlign={["right", "right", "right"]}
            rows={[
              ["3", "4", "0.4%"],
              ["4", "33", "3.3%"],
              ["5", "409", "41.1%"],
              ["6", "174", "17.5%"],
              ["7", "341", "34.3%"],
              ["8", "30", "3.0%"],
            ]}
          />
          <Text size="small" tone="tertiary">
            Mean opponent level 5.91 across 991 combat losses. The most
            common pairing is a level-8 agent losing to a level-7 board
            (341 games).
          </Text>
        </Stack>
      </Grid>
    </Stack>
  );
}
