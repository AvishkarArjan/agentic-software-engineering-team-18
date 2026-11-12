"""Offline checks for chunk limits, fusion, source mapping and evaluation."""
import numpy as np
import pytest

from task3_rag.retrieval import chunk_corpus, lexical_tokens, scale, Retriever, Chunk, tokens
from task3_rag.evaluate import context_recall, context_precision, evaluate
from task3_rag.judge import stratified_sample


@pytest.mark.parametrize('recursive',[True,False])
def test_chunk_limits_and_document_provenance(recursive):
    docs=[{'doc_id':'d1','type':'config','title':'spool.buffer_bytes','version':'2.x',
           'text':'# Header\n\n'+('Paragraph sentence. Another sentence!\n\n'*150)}]
    chunks=chunk_corpus(docs,120,20,recursive)
    assert len(chunks)>1
    assert all(len(tokens(c.text))<=120 and c.doc_id=='d1' and '2.x' in c.text for c in chunks)
    assert len({c.chunk_id for c in chunks})==len(chunks)


def test_exact_identifier_and_component_tokens():
    ts=lexical_tokens('PQ-E4663 spool.buffer_bytes')
    assert {'pq-e4663','spool.buffer_bytes','pq','e4663','spool','buffer','bytes'} <= set(ts)


def test_scaling_is_affine_invariant_and_constant_safe():
    x=np.array([1,4,9])
    assert np.allclose(scale(x),scale(x*100+70))
    assert np.all(scale([2,2,2])==0)


def test_unique_documents_keep_rank_and_chunk_source():
    chunks=[Chunk('a:0','a','foo one'),Chunk('a:1','a','foo two'),Chunk('b:0','b','bar')]
    retriever=Retriever(chunks,np.array([[1.,0],[.9,.1],[0,1]]))
    hits=retriever.retrieve('foo',np.array([1.,0]),mode='dense',k=2)
    assert [h['doc_id'] for h in hits]==['a','b']
    assert hits[0]['chunk_id']=='a:0'


def test_multi_hop_group_recall_and_rank_precision():
    groups=[['a','b'],['c']]
    assert context_recall(['b'],groups)==.5
    assert context_recall(['b','c'],groups)==1
    assert context_precision(['x','b','c'],groups)==pytest.approx((.5+2/3)/2)


def test_evaluation_excludes_unanswerable_and_dedupes():
    qs=[{'id':'q1','category':'identifier','relevant_doc_ids':[['a'],['b']]},
        {'id':'q2','category':'unanswerable','relevant_doc_ids':[]}]
    report=evaluate([{'id':'q1','retrieved_doc_ids':['a','a','b']}],qs,2)
    assert report['summary']['overall']['n']==1
    assert report['summary']['overall']['context_recall']==1
