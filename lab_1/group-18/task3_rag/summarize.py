"""Make reproducible result tables and cost summaries from saved experiment files."""
from collections import defaultdict
import csv
import json
from pathlib import Path

from task3_rag.evaluate import load_jsonl

HERE=Path(__file__).resolve().parent
R=HERE/'results'


def mean(xs):
    return sum(xs)/len(xs) if xs else 0.


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def summarize():
    configs=['r1','r2','r3_120','r3_220','r3_360','r3','r4','r5']
    rows=[]
    for name in configs:
        for split in ('all_dev','tuning','heldout'):
            path=R/f'metrics_{name}_{split}.json'
            if not path.exists(): continue
            s=json.loads(path.read_text())['summary']
            for category,m in {'OVERALL':s['overall'],**s['per_category']}.items():
                rows.append({'configuration':name,'split':split,'category':category,**m})
    with (R/'retrieval_metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['configuration','split','category','n','context_recall','context_precision'])
        w.writeheader(); w.writerows(rows)
    lines=['# Task 3 measured results','', '## Retrieval on held-out development questions','',
           'Values are recall@5 / rank-aware precision@5. Unanswerable questions are excluded by the supplied evaluator.','']
    display=[]
    for name in configs:
        by={r['category']:r for r in rows if r['configuration']==name and r['split']=='heldout'}
        display.append([name]+[f"{by[c]['context_recall']:.3f} / {by[c]['context_precision']:.3f}" for c in ('OVERALL','identifier','paraphrase','multi-hop','version')])
    lines += [table(['Config','Overall','Identifier','Paraphrase','Multi-hop','Version'],display),'']
    if (R/'index_timing.json').exists():
        indexes=json.loads((R/'index_timing.json').read_text())
        selection=json.loads((R/'selection.json').read_text())
        selected=selection['selected_recursive']
        index_rows=[]
        for name in ('r1','r2','r3_120','r3_220','r3_360','r3','r4','r5'):
            if name=='r1':
                path=R/'lexical_index_timing.json'
                if path.exists():
                    m=json.loads(path.read_text());index_rows.append([name,m['chunks'],f"{m['total_s']:.3f}",0,0,'offline BM25 timing'])
                continue
            key=selected if name in ('r3','r4','r5') else name
            m=indexes[key]
            index_rows.append([name,m['chunks'],f"{m['indexing_s']:.3f}",m['embedding']['new'],m['embedding']['local_cache_hits'],'shared '+selected if name in ('r3','r4','r5') else key])
        lines += ['## Index construction','',table(['Config','Chunks','Index seconds','New vectors','Cached vectors','Index reference'],index_rows),'',
                  'R3/R4/R5 share the selected base index; their repeated times describe the same construction, not three independent builds. Later chunk-size settings reuse identical text vectors. R2 indexing time excludes its preceding chunk-construction step; recursive timings include it. R1 is measured separately without vector construction.','']
    lines += ['## Retrieval on all 150 development questions (120 answerable)','',
              'These numbers include the tuning subset; use the held-out table above for comparison without parameter-tuning overlap.','']
    display=[]
    for name in configs:
        by={r['category']:r for r in rows if r['configuration']==name and r['split']=='all_dev'}
        display.append([name]+[f"{by[c]['context_recall']:.3f} / {by[c]['context_precision']:.3f}" for c in ('OVERALL','identifier','paraphrase','multi-hop','version')])
    lines += [table(['Config','Overall','Identifier','Paraphrase','Multi-hop','Version'],display),'']
    if (R/'timing.jsonl').exists():
        from common.llm_client import count_tokens
        from task3_rag.run_experiments import ANSWER_SYSTEM
        questions={q['id']:q for q in load_jsonl(HERE/'data/questions_dev.jsonl')}
        times=load_jsonl(R/'timing.jsonl'); groups=defaultdict(list)
        for x in times: groups[x['configuration']].append(x)
        timing_rows=[]
        for name,items in groups.items():
            scoring=[x['scoring_s'] for x in items]
            estimated=[sum(x[k] for k in ('scoring_s','query_embedding_amortized_s','rewrite_s','rewrite_embedding_amortized_s')) for x in items]
            retrieval=load_jsonl(R/f'retrieval_{name}.jsonl')
            prompt_estimates=[count_tokens(ANSWER_SYSTEM+'QUESTION:\n'+questions[r['id']]['question']+'\n\nDOCUMENTATION EXCERPTS:\n'+'\n\n---\n\n'.join(r['contexts'])) for r in retrieval]
            timing_rows.append([name,f'{mean(scoring)*1000:.3f}',f'{mean(estimated):.3f}',f'{mean([x["context_tokens"] for x in items]):.1f}',f'{mean(prompt_estimates):.1f}'])
        lines += ['## Latency and retrieved context size','',table(['Config','Mean local scoring ms','Mean composed query seconds','Mean context tokens','Approx generator input tokens/query'],timing_rows),'',
                  'Composed query time sums measured scoring, batch-amortized query embedding, and (R5) actual rewrite request/wait time plus batch-amortized rewrite embedding. It is not a measured single-request production latency. Shared embeddings are charged to each dense configuration analytically; no double API billing is implied. Query vectors are reused for fair score comparisons.','']
    cost=defaultdict(lambda:{'calls':0,'prompt_tokens':0,'completion_tokens':0,'reasoning_tokens':0,'cost_usd':0.,'cost_missing':0,'cache_indicator_true':0})
    for path in (HERE/'logs').glob('*.jsonl'):
        phase='embedding' if path.stem=='embeddings' else path.stem.split('_')[0]
        for event in load_jsonl(path):
            if event.get('type') not in ('chat','embedding'): continue
            g=cost[phase];g['calls']+=1
            usage=event.get('usage',{})
            for k in ('prompt_tokens','completion_tokens','reasoning_tokens'):g[k]+=usage.get(k) or 0
            g['cost_usd']+=event.get('cost_usd') or 0
            g['cost_missing']+=event.get('cost_usd') is None
            g['cache_indicator_true']+=event.get('cache_hit') is True
    (R/'cost_summary.json').write_text(json.dumps(cost,indent=2)+'\n',encoding='utf-8')
    lines += ['## Gateway usage','',table(['Phase','Logged operations','Prompt tokens','Completion tokens','Reported USD','Missing cost fields'],
        [[phase,v['calls'],v['prompt_tokens'],v['completion_tokens'],f"{v['cost_usd']:.6f}",v['cost_missing']] for phase,v in cost.items()]),'',
        'Embedding operations may contain multiple HTTP batches. Reasoning tokens are included in completion-token accounting by the gateway; do not add them twice. Costs are gateway-reported, not estimated prices. The helper cache_hit field is only its response-header heuristic; it is not proof of a cold request. Local vector cache hits are recorded separately.','']
    judge_display=[]
    for name in ('r1','r2','r3','r4','r5'):
        path=R/f'judge_{name}.jsonl'
        if not path.exists():continue
        items=load_jsonl(path)
        for category in ['OVERALL']+sorted({r['category'] for r in items}):
            subset=items if category=='OVERALL' else [r for r in items if r['category']==category]
            faith=[r['faithfulness'] for r in subset if r['faithfulness'] is not None]
            judge_display.append([name,category,len(subset),sum(r['abstained'] for r in subset),f'{mean(faith):.3f}' if faith else '-',f'{mean([r["answer_relevance"] for r in subset]):.3f}',f'{mean([r["correctness"] for r in subset]):.3f}'])
    if judge_display: lines += ['## End-to-end judge (same stratified 50 questions, seed 0)','',table(['Config','Category','N','Abstained','Faithfulness','Relevance','Correctness'],judge_display),'']
    per_config=[]
    for name in ('r1','r2','r3','r4','r5'):
        values={'configuration':name,'retrieval_rewrite_usd':0.,'generation_usd':0.,'judge_usd':0.,'rewrite_prompt_tokens':0,'rewrite_completion_tokens':0}
        for path in (HERE/'logs').glob('*.jsonl'):
            phase=None
            if name=='r5' and path.stem.startswith('rewrite_'): phase='retrieval_rewrite'
            if path.stem.startswith(f'generate_{name}_'): phase='generation'
            if path.stem.startswith(f'judge_{name}_'): phase='judge'
            if not phase:continue
            for event in load_jsonl(path):
                if event.get('type') not in ('chat','embedding'):continue
                values[phase+'_usd']+=event.get('cost_usd') or 0
                if phase=='retrieval_rewrite':
                    values['rewrite_prompt_tokens']+=event.get('usage',{}).get('prompt_tokens') or 0
                    values['rewrite_completion_tokens']+=event.get('usage',{}).get('completion_tokens') or 0
        per_config.append(values)
    with (R/'cost_per_configuration.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(per_config[0]));w.writeheader();w.writerows(per_config)
    lines += ['## Costs attributed to configurations','',table(['Config','Retrieval rewrite USD','Generation USD','Judge USD'],
        [[r['configuration']]+[f'{r[k]:.6f}' for k in ('retrieval_rewrite_usd','generation_usd','judge_usd')] for r in per_config]),'',
        'Shared corpus/query embeddings are free on this gateway and reported separately above. R1 performs no API calls at retrieval time. R2/R3/R4 use a query embedding; R5 also uses a rewrite chat call and second query embedding. R5 rewrite cost here covers 150 dev plus 100 test queries. Generation/judge costs reflect only configurations actually run, including test generation for the winner; zeros for other configurations mean not run, rather than a measured zero-cost generation.','']
    (HERE/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Wrote RESULTS.md, results/retrieval_metrics.csv, results/cost_summary.json')


if __name__=='__main__':summarize()
