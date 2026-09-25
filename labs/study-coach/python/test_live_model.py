"""Calls the installed model; records actual outputs, not mocked completions."""
import asyncio,json,time
from pathlib import Path
from ollama_agent import Budget,execute_tool,tool_answer,generate_evidence,MODEL
root=Path(__file__).resolve().parent
async def main():
    report={'model':MODEL,'external_api_spend':0,'spend_note':'Local inference; hardware/electricity cost is not measured.','cases':[]}
    began=time.monotonic()
    tool=await tool_answer('Use lookup_definition to explain checkpoint. Call the tool before answering.')
    assert tool['tool_used'] and tool['budget']['tool_calls']==1 and tool['budget']['model_calls']==2
    assert 'checkpoint' in tool['answer'].lower()
    report['tool_call']=tool
    examples=[('What is a checkpoint?',[{'id':'checkpoint','text':'A checkpoint saves workflow state so a process can resume after a restart. External side effects still require idempotency keys.'}]),
              ('Explain a transaction.',[{'id':'transaction','text':'A transaction commits related database changes together or rolls them back.'}])]
    for question,evidence in examples:
        events=[event async for event in generate_evidence(question,evidence)]
        answer=''.join(x.get('delta','') for x in events)
        assert events[-1]['done'] and events[-1]['citation_gate']
        assert events[-1]['generated_tokens']<=128 and len([x for x in events if 'delta' in x])==1 and events[-1]['requires_review']
        report['cases'].append({'question':question,'answer':answer,'usage':events[-1]})
    for call in [{'function':{'name':'delete_files','arguments':{}}},{'function':{'name':'lookup_definition','arguments':{'term':'checkpoint','owner':'bob'}}}]:
        try:execute_tool(call,Budget())
        except ValueError:pass
        else:raise AssertionError('untrusted tool request accepted')
    report['passed']=['actual model tool call','bounded two-call harness','actual generation buffered until citation-format checks complete','citation-ID gate','unknown tool and forged argument rejection']
    report['seconds']=round(time.monotonic()-began,2)
    report['quality_limit']='Two development questions and mechanical gates; not a broad factuality benchmark. Read the actual answers for semantic review.'
    (root/'live-model-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
asyncio.run(main())
