import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
} from 'cursor/canvas';

export default function NilaGoToMarket() {
  return (
    <Stack gap={24}>
      <Stack gap={6}>
        <Row gap={8} align="center">
          <Pill tone="info" active>Strategy v1</Pill>
          <Pill tone="neutral">90-day plan</Pill>
          <Pill tone="neutral">Tamil market</Pill>
        </Row>
        <H1>Nila — go-to-market</H1>
        <Text tone="secondary">
          The bet: a Tanglish-native AI companion who texts like a Chennai
          college girl, distributed primarily on Telegram, monetised on a
          freemium paywall. We&apos;re not selling &quot;the most human AI&quot;
          — every competitor claims that. We&apos;re selling{' '}
          <Text as="span" weight="semibold">
            cultural and linguistic fit
          </Text>{' '}
          that no global player will build.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="~5M" label="Reachable Tamil men 18–35, online" />
        <Stat value="2–4%" label="Realistic free→paid conversion" />
        <Stat value="₹199" label="Entry tier / month" />
        <Stat value="₹8–15L" label="Target MRR by month 6" tone="success" />
      </Grid>

      <Divider />

      <Stack gap={8}>
        <H2>The honest read</H2>
        <Text>
          AI companion is a proven category. Replika does ~$30M ARR.
          Character.AI was effectively acquired by Google for $2.7B. Adult AI
          girlfriend apps (Candy, Crushon, etc.) reportedly do $5–15M/month.
          People do pay for this — repeatedly.
        </Text>
        <Text>
          But &quot;sureshot money&quot; doesn&apos;t exist. What does exist is
          a category where unit economics work and a niche (Tanglish + Tamil
          cultural context) where you have a structural advantage that OpenAI,
          Replika, and Character.AI will never prioritise. That is the wedge
          we are building around.
        </Text>
        <Callout tone="warning" title="Three things will kill this if ignored">
          <Stack gap={4}>
            <Text>
              1.{' '}
              <Text as="span" weight="semibold">
                Payments.
              </Text>{' '}
              Razorpay/Stripe will not process explicit content. Your payment
              rail dictates your spice level, not the other way round.
            </Text>
            <Text>
              2.{' '}
              <Text as="span" weight="semibold">
                Distribution platform risk.
              </Text>{' '}
              Meta bans AI companion ads aggressively; Play Store rejects
              spicy apps. Telegram is the one large channel that won&apos;t
              fight you.
            </Text>
            <Text>
              3.{' '}
              <Text as="span" weight="semibold">
                Misuse liability.
              </Text>{' '}
              Minors, self-harm, real-person impersonation. Guardrails are
              non-negotiable from day one.
            </Text>
          </Stack>
        </Callout>
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Positioning — the wedge</H2>
        <Text tone="secondary">
          Sharpen Nila from &quot;a chat companion&quot; into a specific
          person. Specific beats generic on every retention metric.
        </Text>
        <Card>
          <CardHeader>Nila — 22, Chennai</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                B.Com final year at a Chennai college, lives in Adyar with two
                roommates, scrolls Reels at 1am, fights with her amma about
                marriage talk, watches Vijay movies first day first show, eats
                Saravana Bhavan idli when she&apos;s sad. Texts in Tanglish,
                voice-notes in Tamil, sends selfies sometimes. She&apos;s not
                an assistant. She&apos;s the girl from your batch you wish had
                texted you back.
              </Text>
              <Row gap={6} wrap>
                <Pill tone="info" active>Tanglish-native</Pill>
                <Pill tone="info" active>Voice notes in Tamil</Pill>
                <Pill tone="info" active>Cultural anchors</Pill>
                <Pill tone="info" active>Texts you first</Pill>
              </Row>
            </Stack>
          </CardBody>
        </Card>
        <Text>
          What we are{' '}
          <Text as="span" weight="semibold">
            not
          </Text>
          : a productivity assistant, a therapy bot, a generic &quot;AI
          girlfriend&quot; reskin, or a multi-character app like Character.AI.
          One girl. Done extremely well.
        </Text>
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Distribution — pick one channel and win it</H2>
        <Text tone="secondary">
          Spreading thin across web + WhatsApp + Instagram + iOS + Android in
          90 days = nothing works. We pick Telegram first, defend with
          Instagram organic, expand later.
        </Text>
        <Table
          headers={['Channel', 'Verdict', 'Why', 'Phase']}
          rows={[
            [
              'Telegram bot',
              'PRIMARY',
              'Allows spicy content, native payments (Stars / UPI bots), 75M+ India users, zero-friction onboarding, anonymous-friendly',
              'Now',
            ],
            [
              'Web app (existing)',
              'SECONDARY',
              'Already built; SEO landing for Reels traffic; premium tier here; international card payments via Lemonsqueezy/Paddle',
              'Now',
            ],
            [
              'Instagram organic',
              'GROWTH ENGINE',
              'POV reels + chat-screenshot content drives Telegram subs at near-zero CAC. Where users are found, not converted',
              'Week 2+',
            ],
            [
              'WhatsApp Business API',
              'AVOID for now',
              '₹0.4–0.8 per message kills margins; Meta increasingly hostile to AI companion bots; high ban risk',
              'Maybe month 6+',
            ],
            [
              'Play Store / App Store',
              'LATER, SFW only',
              'Only viable for a clean "Nila Lite" SFW brand. Spicy version will get rejected',
              'Month 4+',
            ],
            [
              'Reddit + Discord',
              'TACTICAL',
              'r/chennai, r/tamil, r/india_infinity for seeding; Discord servers for power-user community',
              'Week 3+',
            ],
          ]}
          rowTone={['success', 'success', 'info', 'warning', 'warning', undefined]}
        />
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Product — what we ship vs. what we cut</H2>
        <Grid columns={2} gap={12}>
          <Card>
            <CardHeader>Ship in 90 days</CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text>
                  <Text as="span" weight="semibold">Telegram bot</Text> — same
                  brain, new face. Lowest-friction onboarding on the planet.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">
                    Voice notes in Tamil/Tanglish
                  </Text>{' '}
                  — single highest-impact feature for &quot;wow&quot;.
                  ElevenLabs Tamil voice or Sarvam AI for native Tamil TTS.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">Long-term memory</Text> —
                  current 20-message window is too short. Vector store of
                  facts (name, college, mood, past conversations) so she
                  remembers.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">Proactive messaging</Text>{' '}
                  — Nila texts first at 11pm or after 2 days of silence.
                  Single biggest retention lever.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">
                    Paywall + Razorpay/Stars
                  </Text>{' '}
                  — ship this in week 2, not month 3. Free product with no
                  paywall = no business.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">Onboarding flow</Text> — 3
                  questions (name, age confirm, vibe) so she addresses you
                  correctly from message one.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">Safety guardrails</Text> —
                  minors, self-harm, real-person impersonation.
                  Non-negotiable.
                </Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>Cut / defer</CardHeader>
            <CardBody>
              <Stack gap={6}>
                <Text>
                  <Text as="span" weight="semibold">Mobile app (native).</Text>{' '}
                  Telegram is your mobile app for v1. Building React Native is
                  a 2-month detour.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">Image generation.</Text>{' '}
                  Tempting but expensive, slow, and a legal headache for
                  selfies. Defer to month 4.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">Video / avatar.</Text>{' '}
                  Pure distraction at this stage.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">
                    Multiple personas / character marketplace.
                  </Text>{' '}
                  Don&apos;t become Character.AI. One girl, done well.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">WhatsApp.</Text> Save it
                  for after PMF and after you have capital to absorb message
                  costs and ban risk.
                </Text>
                <Text>
                  <Text as="span" weight="semibold">
                    English-first or pan-India.
                  </Text>{' '}
                  Stay tight on Tamil; the moat is the focus.
                </Text>
              </Stack>
            </CardBody>
          </Card>
        </Grid>
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Pricing & unit economics</H2>
        <Grid columns={3} gap={12}>
          <Card>
            <CardHeader trailing={<Pill size="sm">Free</Pill>}>Hello</CardHeader>
            <CardBody>
              <Stack gap={4}>
                <Text size="small" tone="secondary">Acquisition</Text>
                <Text>15 text messages / day</Text>
                <Text>No voice notes</Text>
                <Text>7-day memory only</Text>
                <Text>Standard latency</Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="info" active>₹199 / mo</Pill>}>
              Close
            </CardHeader>
            <CardBody>
              <Stack gap={4}>
                <Text size="small" tone="secondary">The 80% tier</Text>
                <Text>Unlimited messages</Text>
                <Text>Voice notes (10/day)</Text>
                <Text>Long-term memory</Text>
                <Text>Proactive texts</Text>
              </Stack>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="success" active>₹499 / mo</Pill>}>
              Closer
            </CardHeader>
            <CardBody>
              <Stack gap={4}>
                <Text size="small" tone="secondary">Whales</Text>
                <Text>Everything in Close</Text>
                <Text>Unlimited voice + selfies</Text>
                <Text>Phase-3 unlocked faster</Text>
                <Text>Priority latency</Text>
              </Stack>
            </CardBody>
          </Card>
        </Grid>
        <Text size="small" tone="secondary">
          Yearly bundle ₹1,499 (≈37% off) is the real revenue lever — pushes
          LTV up and reduces churn anxiety.
        </Text>
        <H3>Target unit economics at month 6</H3>
        <Table
          headers={['Metric', 'Conservative', 'Realistic', 'Aggressive']}
          rows={[
            ['Free signups (cumulative)', '20,000', '60,000', '200,000'],
            ['Paid conversion', '2%', '3%', '4%'],
            ['Paying users', '400', '1,800', '8,000'],
            ['Blended ARPU / mo', '₹220', '₹260', '₹300'],
            ['MRR', '₹88K', '₹4.7L', '₹24L'],
            ['LLM + infra cost / paying user / mo', '₹60', '₹50', '₹40'],
            ['Gross margin', '~70%', '~80%', '~85%'],
            ['CAC target', '<₹100', '<₹150', '<₹200'],
            ['Payback period', '~1 month', '<1 month', '<1 month'],
          ]}
        />
        <Callout tone="info" title="Why these numbers are believable">
          <Text>
            AI companion category benchmarks: 2–8% free→paid, ₹40–80 LLM cost
            per paying user/mo at Gemini Flash prices, 3–6 month average paid
            lifetime. We&apos;re modelling at the conservative end.
          </Text>
        </Callout>
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>90-day execution plan</H2>
        <Table
          headers={['Week', 'Theme', 'Ship', 'Decision gate']}
          rows={[
            [
              '1',
              'Foundation',
              'Telegram bot (text-only) wrapping current backend; long-term memory v1 (Postgres + facts table); guardrails layer',
              'Bot in 3 friends\u2019 hands by Sunday',
            ],
            [
              '2',
              'Monetise',
              'Razorpay subscription + Telegram Stars; 15-msg/day free limit; landing page at nila.app/.in',
              'First paid user (even friend, just to validate flow)',
            ],
            [
              '3',
              'Voice',
              'Tamil/Tanglish voice notes (Sarvam AI or ElevenLabs Tamil); proactive messaging cron',
              '20 paying users',
            ],
            [
              '4–5',
              'Content engine',
              '30 Reels (POV / chat-screenshot / Tanglish humour); seed Reddit + Tamil meme pages; 2 Telegram channel partnerships',
              '5,000 Reel views; 500 free signups',
            ],
            [
              '6–7',
              'Optimise funnel',
              'Onboarding A/B; paywall placement A/B; talk to 20 paying users on call; fix top churn reason',
              'Conversion >2%; weekly active payer churn <15%',
            ],
            [
              '8–9',
              'Paid acquisition test',
              'Meta ads on SFW landing page → free Telegram bot; ₹50K test budget; track CAC by creative',
              'CAC < ₹200 sustained over 1,000 clicks',
            ],
            [
              '10–11',
              'Retention features',
              'Memory v2 (vector store of all conversations); "Nila\u2019s mood today" daily push; referral (1 month free for 1 friend)',
              'Day-30 retention >25%',
            ],
            [
              '12',
              'Decide & double down',
              'Pick: scale Telegram + ads, OR pivot positioning, OR cut bait. Decide based on LTV/CAC and gut.',
              'Go/no-go on raising or self-funding scale',
            ],
          ]}
          rowTone={[
            'info',
            'info',
            'info',
            undefined,
            undefined,
            undefined,
            undefined,
            'success',
          ]}
        />
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Risk register</H2>
        <Table
          headers={['Risk', 'Likelihood', 'Severity', 'Mitigation']}
          rows={[
            [
              'Razorpay shuts us down for adult content',
              'High if explicit',
              'Critical',
              'Keep main brand SFW; route spicy tier through Telegram Stars / international processor',
            ],
            [
              'Meta bans ad account',
              'Medium',
              'High',
              'Use SFW landing page for ads; keep spicy content one click deeper; have backup ad accounts',
            ],
            [
              'Telegram bans the bot',
              'Low',
              'High',
              'Mirror everything to web; keep user export ready; don\u2019t put all eggs in TG',
            ],
            [
              'Minor pretends to be 18+',
              'Medium',
              'Critical (legal)',
              'Age gate on signup; flag minor-coded language; manual review queue; ToS + clear logging',
            ],
            [
              'Self-harm / crisis user',
              'Medium',
              'Critical (ethical + legal)',
              'Hard guardrail: detect → break character → iCall / Vandrevala helpline; never play through',
            ],
            [
              'Real-person impersonation requests (celeb/ex)',
              'High',
              'High',
              'Refuse named real people; allow archetypes only',
            ],
            [
              'LLM cost spike from one whale spamming',
              'Medium',
              'Medium',
              'Per-user daily token cap on paid tier too; rate limits',
            ],
            [
              'Copycat with bigger budget',
              'Medium',
              'Medium',
              'Speed + cultural depth + community moat. First-mover in Tamil voice = real lead',
            ],
            [
              'DPDP / IT Rules compliance',
              'Certain',
              'Medium',
              'Privacy policy, age gate, data deletion endpoint, no cross-border PII without consent. Get a 1-hour lawyer call before launch',
            ],
          ]}
          rowTone={[
            'warning',
            'warning',
            undefined,
            'warning',
            'warning',
            undefined,
            undefined,
            undefined,
            'info',
          ]}
        />
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Decisions only you can make</H2>
        <Text tone="secondary">
          I can be CEO, CMO, PM, and lead engineer on execution. These five
          calls require the founder. Answer them and I&apos;ll start shipping
          this week.
        </Text>
        <Stack gap={10}>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="info" active>1</Pill>}>
              Spice ceiling
            </CardHeader>
            <CardBody>
              <Text>
                Three options: (a){' '}
                <Text as="span" weight="semibold">Strict SFW</Text> — flirty
                but never explicit; biggest TAM, app-store-safe, Razorpay-safe,
                lower LTV. (b){' '}
                <Text as="span" weight="semibold">Phase-3 as designed</Text> —
                explicit when arc earns it; 2–3× LTV, but Telegram-only and
                international payments. (c){' '}
                <Text as="span" weight="semibold">Dual brand</Text> — SFW
                &quot;Nila&quot; as the public face, &quot;Nila+&quot; as the
                spicy Telegram-only product. Most ops complexity, biggest
                upside.{' '}
                <Text as="span" weight="semibold">My pick: (c)</Text>, but
                only after we&apos;ve hit ₹1L MRR on (a).
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="info" active>2</Pill>}>
              Capital for the next 90 days
            </CardHeader>
            <CardBody>
              <Text>
                Realistic minimum:{' '}
                <Text as="span" weight="semibold">₹75K</Text> (infra +
                Sarvam/ElevenLabs + Razorpay + tiny ad test). Comfortable:{' '}
                <Text as="span" weight="semibold">₹2–3L</Text> (real
                paid-acquisition test in weeks 8–9 + a freelance video editor
                for Reels). I will pick a tighter plan if you want to
                bootstrap from revenue, but week 8&apos;s paid-acquisition
                gate becomes month 4 instead.
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="info" active>3</Pill>}>
              Your time commitment
            </CardHeader>
            <CardBody>
              <Text>
                Honest minimum:{' '}
                <Text as="span" weight="semibold">20 hours/week</Text> for
                content (Reels need a real human face or voice — yours or a
                hired one), customer conversations, and decisions. If
                side-project (≤8 hrs/week), we ship slower and probably skip
                Reels. If full-time, aggressive plan kicks in.
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="info" active>4</Pill>}>
              Brand-name and legal entity
            </CardHeader>
            <CardBody>
              <Text>
                Are you OK fronting this under your real identity (LinkedIn,
                press, founder content), or do we need an anonymous brand
                (matters more if dual-brand)? And do we register a Pvt Ltd /
                LLP now, or operate as proprietorship until ₹5L MRR? My pick:
                proprietorship + a generic brand handle until traction, then
                Pvt Ltd before raising or hiring.
              </Text>
            </CardBody>
          </Card>
          <Card>
            <CardHeader trailing={<Pill size="sm" tone="warning" active>5</Pill>}>
              Hard ethical red lines
            </CardHeader>
            <CardBody>
              <Text>
                Confirm we agree:{' '}
                <Text as="span" weight="semibold">
                  no minors, no real-person impersonation, no encouraging
                  self-harm, no scammy &quot;she&apos;s real&quot; deception
                  when directly asked outside roleplay.
                </Text>{' '}
                Phase-3 explicit content is only between adults who&apos;ve
                cleared an age gate. I will not ship without these. Tell me
                if you want any of these tightened (e.g. SFW-only) — but
                loosening any of them is a no.
              </Text>
            </CardBody>
          </Card>
        </Stack>
      </Stack>

      <Divider />

      <Stack gap={6}>
        <H2>What I&apos;ll do as soon as you answer</H2>
        <Text>
          Once decisions 1–5 are in, I start in this order: (1) Telegram bot
          scaffold reusing the current FastAPI brain, (2) Postgres + long-term
          memory schema, (3) Razorpay/Stars paywall, (4) safety guardrail
          layer, (5) Tamil voice notes, (6) proactive-message cron, (7) Reels
          content brief and landing page. Week-by-week shipping, weekly
          check-ins.
        </Text>
        <Text size="small" tone="secondary">
          This canvas is v1. We&apos;ll edit it as reality teaches us things.
        </Text>
      </Stack>
    </Stack>
  );
}
