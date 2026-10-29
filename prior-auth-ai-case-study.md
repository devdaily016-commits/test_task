# Prior authorization AI

Case-study handout. The three opportunity briefs are the pages to walk through. The long plans are backup for architecture, evaluation, and Q&A. This page is the shared answer: what we would tell the CMO, what it costs, and why the live demo is intake.

Backup plans:

- Opportunity 1: `opp1_intake_completeness_b3de1620.plan.md`
- Opportunity 2: `opp2_nurse_decision_support_8e565158.plan.md`
- Opportunity 3: `opp3_provider_transparency_8d8612ab.plan.md`

## Answer to the CMO

AI handles the paperwork. Licensed clinicians keep the judgment. The 4.2 days are mostly waiting: for documents to be indexed, for missing information, in the nurse queue, and on status calls. AI reads every fax and PDF on day 0 and sends back what is missing. On complete packets it assembles the evidence for each criterion, with the page it came from. It can auto-approve only cases that are clearly low-risk and clearly meet criteria. Every adverse decision stays with a licensed clinician. The models run as Claude on Amazon Bedrock under the AWS BAA. Prompts are not used to train the model. There is no GPU fleet to operate. Run cost scales with volume: about $0.20–$1.20 per request all-in, against many times that in nurse and intake time.

## The three opportunities

| | What it does | Turnaround | Run cost at 15k requests / month |
| --- | --- | --- | --- |
| 1. Intake and completeness | Reads the fax, extracts the request, and flags missing documents before a nurse opens it | about 0.7 days | $0.3k–$3k |
| 2. Nurse decision support | Lays cited evidence against a versioned criteria tree. Code computes the result. Nurses confirm. Physicians own adverse decisions | about 1.0 day | $1.2k–$10.5k |
| 3. Provider status | Portal, FHIR status, and a Haiku agent that answers "where is my auth?" after a code-enforced login | about 0.1–0.2 days | $50–$500 for chat. Voice adds $1.5k–$4k |

Together, about 4.2 days down to about 2.4 days (−43%), with no new headcount. That clears the 40% reduction leadership asked for.

We prototype Opportunity 1. It is the fastest to show, needs no licensed clinical criteria, never makes a coverage decision, and is the most visual in 15 minutes. Opportunity 2 is the slide the CMO will push on. Opportunity 3 is the slide operations will push on.

One service line carries the story: lumbar epidural steroid injection, CMS LCD L39240 (revision effective April 16, 2026; billing article A58993). Public CMS text only. InterQual and MCG stay behind the vendor API in production.

## Platform

Managed Claude, open-source everything else.

- Bedrock is on the AWS HIPAA-eligible services list. Sign the BAA in AWS Artifact before any PHI moves. Pin a US region and use in-region inference so PHI stays there. In-region list prices are about 10% above the global rate. Invocation logging stays off, or goes only to an encrypted, access-restricted S3 bucket. Traffic uses VPC PrivateLink. The public Anthropic API and consumer chat products are out of the production path. They do not carry our BAA.
- The prototype may call the Anthropic API because the packets are synthetic and watermarked. That exception is for the demo only.
- Every model call goes through LiteLLM. Azure OpenAI or Gemini on Vertex can be swapped by configuration. Re-run the evaluation suite before any model change.
- Model tiering, Bedrock in-region list prices, October 2026, per million input / output tokens:
  - Claude Haiku 5.5, $0.11 / $0.55 (5× above 100k tokens in a prompt): extraction, classification, completeness mapping, status chat. Split large packets so they stay under 100k.
  - Claude Sonnet 5.5, $2.20 / $11: per-criterion clinical evidence, and vision on bad fax pages. Cache reads are $0.11 per million, so cache the policy text and the system prompt.
  - Claude Opus 5.5, $4.40 / $22: hard cases and the evaluation judge only.
  - Batch is 50% off and is for retrospective evaluation and backfills. Live decisions stay synchronous.
- Open source stays on OCR and layout (Docling + PaddleOCR), orchestration (LangGraph now, Temporal in production), FHIR (HAPI, Da Vinci PAS), the UI, evaluation (Langfuse in our VPC, promptfoo or DeepEval), identity (Keycloak), and PHI redaction (Presidio). Embeddings default to local BGE-M3 so retrieval cost stays at zero.
- Self-hosting the model is the wrong default at this volume. Two production GPUs plus half a platform engineer run about $20k–$40k a month before the first request, and open-weight models still trail Sonnet on long-chart reasoning. Revisit self-hosting above 50k requests a month, or if counsel forbids PHI leaving the VPC even to a BAA vendor.

## Baseline (assumptions labeled)

Volume is 15,000 requests a month. A 22% rework rate is about 3,300 requests sent back to the provider.

Rough split of the 4.2 days:

| Slice | Days |
| --- | --- |
| Intake and indexing | 0.7 |
| Rework, averaged across all cases | 0.5 |
| Nurse queue and review | 2.2 |
| Physician review and notification | 0.8 |

Industry anchors, for questions: AMA 2025, 40 prior auths per physician per week and 13 hours; CAQH Index 2024, a manual prior auth costs the plan $3.41 versus $0.05 electronic, and the provider $12.88 versus $5.38; KFF, 80.7% of Medicare Advantage prior-auth appeals were overturned in 2024; Elevance has reported 60% fewer missing-information pends.

## Cost and value

Figures are directional. Token counts are assumptions to replace with Langfuse measurements after the first week of a pilot. Assume 15 pages per request.

**Opportunity 1, intake.** Docling on CPU is $0. Haiku extraction and completeness is about $0.01–$0.03 per request. Sonnet vision on the roughly 20% of packets with bad pages adds about $0.01–$0.02 blended. Monthly: about $0.3k–$0.8k if Haiku goes first, or $1.5k–$3k if Sonnet reads every packet. Do not default to Textract Analyze Document: at $0.05 a page that is about $11k a month on 225k pages. Textract Detect Document Text ($0.0015 a page, about $340 a month) is an optional fallback.

**Opportunity 2, decision support.** This is the token bill. An optimized path (Haiku first, one Sonnet call on unsettled criteria, policy cached, extra samples only when confidence is low) is about $0.08–$0.20 per case, $1.2k–$3k a month. A naive path (Sonnet three times on every criterion) is about $0.30–$0.70 per case, $4.5k–$10.5k a month. Skip Opportunity 2 on packets Opportunity 1 already marked incomplete. Keep the output schema tight: Sonnet output is $11 per million tokens.

**Opportunity 3, transparency.** Haiku is about $0.002–$0.005 per conversation, about $40–$150 a month at 20k–30k conversations. The channel is the cost. Chat and the portal are nearly free. SMS is cents if the body is a secure link and never PHI. Voice (carrier + speech-to-text + text-to-speech) is about $1.5k–$4k a month. Ship chat first.

**Shared infrastructure.** RDS Postgres with pgvector, ECS/Fargate, S3 + KMS, CloudWatch, self-hosted Langfuse and HAPI FHIR: about $1.5k–$3.5k a month.

**Total run cost.** About $3k–$8k a month optimized, or $8k–$18k conservative. About $0.20–$1.20 per request. A demo of all three, including prompt iteration, stays under $200. The intake prototype alone is tens of dollars.

**Value, loaded labor rates as assumptions.**

| Capacity | Monthly value |
| --- | --- |
| Nurses, about 2,500 hours at $55 | about $137k |
| Intake, 1,250–2,500 hours at $30 | about $37k–$75k |
| Status calls, 10k–15k deflected at $5–$7 | about $50k–$100k |

Gross capacity value is about $225k–$310k a month against $3k–$18k of run cost, roughly 15–70× before build cost. The headline for the CMO is absorbing growth and meeting CMS-0057-F's 72-hour and 7-day deadlines without new hires.

**What breaks at 50k requests a month.** Reviewer capacity, checklist ownership, and queue timeouts break before the model does. Add Temporal for pend timers, the Da Vinci PAS API so complete electronic requests skip the fax, reserved Bedrock throughput only after on-demand throttles, and a shadow period before any auto-approval widens.

## Compliance that applies to all three

- HIPAA: BAA before PHI, minimum necessary, encryption, role-based access, a FHIR `AuditEvent` per decision kept 6 years. No unredacted PHI in JSON schemas, tool definitions, or Langfuse.
- CMS-0057-F: 72-hour urgent and 7-day standard deadlines, and specific denial reasons, since January 1, 2026. Metrics were first due March 31, 2026. The FHIR Prior Authorization API is due January 1, 2027.
- CMS-4201-F and the February 2024 FAQ: AI can assist. It cannot deny alone. Coverage criteria must not drift from the published policy.
- State laws to be ready for: California SB 1120, Texas SB 815 ("wholly or partly"), Maryland HB 820, plus Nebraska, Arizona, Washington, and Alabama. NCQA: no AI-only medical-necessity denials.
- Vendor risk: pin model IDs, re-run evaluation before upgrades, keep a documented fallback in LiteLLM.
- Lessons from UnitedHealth/naviHealth, Cigna PxDx, and Humana: no population rule overriding the individual chart, no rubber-stamp review, logs that would survive discovery.

## What the 15-minute demo does not include

HAPI FHIR, Temporal, Da Vinci PAS, the nurse workbench, a voice agent, and auto-approval. Those are the scale path. The demo is a synthetic fax, an extraction, a checklist, and a missing-information letter.
