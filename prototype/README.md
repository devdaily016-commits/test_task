# Intake prototype

Opportunity 1, small enough to show in a few minutes. Three synthetic prior-authorization faxes go in. A checklist for CMS LCD L39240 says what is missing. A letter asks the provider for those documents. Nothing on this screen approves or denies coverage.

The packets are fictional and marked synthetic. Fixture extractions ship with them, so the demo runs with no API key.

## Run

```bash
cd prototype
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_packets.py
pytest
streamlit run app.py
```

`generate_packets.py` rewrites `samples/` and `fixtures/` from `src/packets.py`. Run it again if you change a fax.

## What you are looking at

| Packet | What happens |
| --- | --- |
| Incomplete fax, Jordan Hale | Clean text. Pain is 2 weeks, no conservative care, no MRI report, no baseline score. The letter lists those gaps. |
| Complete packet, Riley Okonkwo | Initial left L5 injection with the MRI attached. The checklist is clear. There is no letter. |
| Degraded fax, Morgan Ellis | Image only. The member ID is covered and the imaging page cannot be read. The fax number is faint, so that field asks for confirmation. |

The model does not decide complete versus incomplete. `checklists/l39240_lumbar_esi.yaml` does. Low-confidence fields and a bad NPI check digit ask a person to look.

## Cost on the screen

The packet figure is an estimate from that file: Haiku 5.5 on a text layer, Sonnet 5.5 vision when the page has no text. Prices are Bedrock in-region list prices for October 2026 ($0.11 / $0.55 and $2.20 / $11 per million tokens). The $0.02 and $300–$800 figures are the production planning range for a 15-page packet, not the cost of these short samples.

## Live Claude

Put a key in `prototype/.env` (`ANTHROPIC_API_KEY`) and choose Live Claude. That call goes to the public Anthropic API. Use it only on these synthetic files. Production is Claude on Amazon Bedrock, in-region, under the AWS BAA, through the same kind of LiteLLM call.

Parsing here is PyMuPDF, because it installs in seconds. PyMuPDF is AGPL. Production parsing is Docling (MIT) plus PaddleOCR, which keeps the page and the bounding box. Vision is the fallback for pages Docling cannot read, which is the degraded sample.

## Out of scope

FHIR, Temporal, a nurse workbench, and auto-approval. Those are the scale path in the briefs, not this folder.
