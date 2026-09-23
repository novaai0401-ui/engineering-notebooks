# User-defined RAG flow lab

The default lab is offline and uses only Python 3.11+ standard library. From the library root:

```shell
python labs/rag-flow/test_flow.py
python labs/rag-flow/rag_flow.py --config labs/rag-flow/flow.json --question "Who leads the team maintaining Orion?"
```

Edit flow.json to choose simple, hybrid, graph, multi_hop, agentic or adaptive. top_k, max_steps, context_chars and explicit subquestions control the bounded flow. The output includes evidence and each routing/retrieval step. --user selects an educational identity fixture; it is not an authentication mechanism.

The default semantic encoder is a transparent synonym/concept demonstration, the graph uses hand-authored entities, and the default agent/router policies are deterministic. Default generation is exact evidence display. Optional real-encoder and model-controller configurations are described below; none is a full Microsoft GraphRAG implementation.

To use the optional local model, run an Ollama server on 127.0.0.1:11434 with qwen2.5:7b-instruct-q4_K_M available, then set generator to ollama. `python labs/rag-flow/run_live.py` attempts four reviewable answers and writes live-report.json only when the run completes; failures go to live-retest-report.json. Two earlier generated answers and their review are preserved in the initial reports. Model weights/runtime are not bundled; downloaded model licensing and hardware needs remain applicable. Successful execution alone does not establish factual quality.

Notebook 30 connects all stages and explains where to replace the teaching interfaces with actual embedding, reranking, structured retrieval and model tool decisions. Inspect report.json and any live-review.json before interpreting results.

Additional real-model checks are now available in test_pretrained.py and test_factual_holdout.py. The former uses actual pretrained MiniLM embeddings and permission-first ranking over a fresh corpus; the latter isolates factual/adversarial generation with eight predeclared question/evidence pairs. The configurable flow also supports optional pretrained-flow.json and model-agent-flow.json: actual embeddings and a validated read-only model controller. test_integrated.py verifies the encoder integration; --model also exercises an actual model-selected tool. The default remains standard-library-only. Graph entities remain curated; no production GraphRAG or general agent-reliability claim is made. See ../RELIABILITY-EXTENSIONS.md for setup and commands, and preserve both automated scores and any explicit human review.

The separate graph_pipeline.py / test_graph_pipeline.py now adds actual model extraction and persistent, permission-filtered graph maintenance. It does not replace the original curated teaching graph. See Notebook 30 for provenance and community-summary limitations.

Generation failures now return explicitly labelled source excerpts with a generation_fallback trace. generation_timeout_seconds defaults to 120 and accepts 1–240 seconds. No permitted evidence skips the model. Run test_generation_recovery.py for injected transport failures; actual model scores remain in the separate factual and development-regression reports, including failed cases.
