# Chat Quote Agent (Complex LangGraph)

The LangGraph implementation of the Chat Quote API main flow — a supervisor/orchestrator
in which a **main agent** drives the conversation and delegates every decision to
**single-purposed specialist tools**.

## Stack

- **Orchestration**: LangGraph (`StateGraph`, typed state, conditional edges)
- **Graph shape**: `understand → route → plan → consult → oversee → decide → respond`

## Set up local Dev environment

```bash
make install
```

## Main Flow Graph

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
        __start__([<p>__start__</p>]):::first
        medical_summary(medical_summary)
        route(route)
        consult(consult)
        rate(rate)
        final_decision(final_decision)
        respond(respond)
        protect(protect)
        __end__([<p>__end__</p>]):::last
        __start__ -.-> medical_summary;
        __start__ -.-> protect;
        consult --> rate;
        final_decision --> respond;
        medical_summary -.-> protect;
        medical_summary -.-> route;
        rate --> final_decision;
        route -.-> consult;
        route -.-> protect;
        route -.-> respond;
        protect --> __end__;
        respond --> __end__;
        classDef default fill:#f2f0ff,line-height:1.2
        classDef first fill-opacity:0
        classDef last fill:#bfb6fc
```