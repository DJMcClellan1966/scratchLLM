# Local-only stack

This project keeps the entire stack local. When adding features or dependencies, follow these rules.

## Rules

1. **No cloud LLM or inference APIs**  
   Do not call OpenAI, Anthropic, or any remote model. All generation is from the locally trained model.

2. **Data fetching is allowed for corpus enrichment**  
   You may fetch content from the internet (e.g. article text from bookmark URLs, RSS, APIs) when it is used only to add data for the local LLM. The model and inference stay local; fetched data is used to build or expand the training corpus.

3. **Local compute only**  
   Training and inference run on the user’s machine. Default to CPU; GPU is optional and still local.

4. **Local dependencies**  
   Prefer libraries that run fully offline (e.g. PyTorch CPU, local BPE). No mandatory phone-home or cloud services.

5. **Data stays on device**  
   Corpus, checkpoints, and config live under the project or user-chosen paths. Nothing is uploaded by default.

## Allowed

- Reading/writing files and directories on the host machine.
- PyTorch (or similar) for model and training, running locally.
- Local tokenizer (BPE trained on corpus, or character-level).
- Optional local GPU for training/inference.
- **Fetching data from the internet** when used only to add info/data for the local LLM (e.g. fetching article content from bookmarks, RSS, or other sources to enrich the corpus).

## Out of scope

- Calling any external API for **generation or embeddings** (the LLM itself is always local).
- Sending corpus or model outputs to a remote service.
