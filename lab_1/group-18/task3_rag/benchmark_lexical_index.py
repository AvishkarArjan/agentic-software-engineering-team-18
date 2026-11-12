"""Offline lexical index build timing; no gateway requests or embeddings."""
import json
from pathlib import Path
import time
from task3_rag.evaluate import load_jsonl
from task3_rag.retrieval import chunk_corpus, Retriever, write_json

HERE=Path(__file__).resolve().parent


def main():
    size=int(json.loads((HERE/'results/selection.json').read_text())['selected_recursive'].split('_')[1])
    docs=load_jsonl(HERE/'data/corpus.jsonl')
    started=time.perf_counter()
    chunks=chunk_corpus(docs,size,32,True)
    chunk_s=time.perf_counter()-started
    started=time.perf_counter()
    index=Retriever(chunks)
    build_s=time.perf_counter()-started
    write_json(HERE/'results/lexical_index_timing.json',{'size':size,'overlap':32,'chunks':len(chunks),'chunking_s':chunk_s,'bm25_build_s':build_s,'total_s':chunk_s+build_s,'gateway_calls':0,'note':'Separate offline timing of BM25 build; dense indexes share embeddings and lexical index in main run.'})
    print(f'BM25: {len(chunks)} chunks, {chunk_s+build_s:.3f}s including chunking.')


if __name__=='__main__':main()
