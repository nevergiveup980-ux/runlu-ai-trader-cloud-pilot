import json
import os
import unittest
from unittest.mock import patch
from model_transport import ChatCompletionsTransport,ModelTransportError
from llm_adapter import JsonResearchAdapter
from agent_runtime import ResearchContext,run_council

class Response:
    def __init__(self,body): self.body=body
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,n): return self.body

def response(content='{"message":"Research only"}',finish='stop'):
    return Response(json.dumps({'choices':[{'finish_reason':finish,'message':{'content':content}}]}).encode())

class TestModelTransport(unittest.TestCase):
    def setUp(self): self.messages=[{'role':'system','content':'research'},{'role':'user','content':'{}'}]
    def test_missing_key_fails_closed(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ModelTransportError): ChatCompletionsTransport(opener=lambda *a,**k:None)(self.messages)
    def test_success_and_no_key_in_body(self):
        def opener(req,timeout):
            self.assertEqual(timeout,20)
            self.assertIn('Bearer SECRET_TEST',req.headers['Authorization'])
            self.assertNotIn(b'SECRET_TEST',req.data)
            self.assertEqual(json.loads(req.data)['response_format'],{'type':'json_object'})
            return response()
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'SECRET_TEST'}):
            self.assertEqual(ChatCompletionsTransport(opener=opener)(self.messages),'{"message":"Research only"}')
    def test_no_unapproved_host(self):
        for endpoint in ['http://api.openai.com/v1/chat/completions','https://evil.example/v1/chat/completions','https://api.openai.com.evil.example/v1/chat/completions','https://api.openai.com/v1/chat/completions?x=1']:
            with self.subTest(endpoint=endpoint),self.assertRaises(ModelTransportError): ChatCompletionsTransport(endpoint=endpoint)
    def test_api_error_redacts_secret(self):
        def bad(*a,**k): raise OSError('SECRET_TEST leaked in network exception')
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'SECRET_TEST'}):
            with self.assertRaises(ModelTransportError) as cm: ChatCompletionsTransport(opener=bad)(self.messages)
        self.assertNotIn('SECRET_TEST',str(cm.exception))
    def test_truncated_response_rejected(self):
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'key'}):
            with self.assertRaises(ModelTransportError): ChatCompletionsTransport(opener=lambda *a,**k:response(finish='length'))(self.messages)
    def test_malformed_response_rejected(self):
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'key'}):
            with self.assertRaises(ModelTransportError): ChatCompletionsTransport(opener=lambda *a,**k:Response(b'bad'))(self.messages)
    def test_oversize_response_rejected(self):
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'key'}):
            with self.assertRaises(ModelTransportError): ChatCompletionsTransport(opener=lambda *a,**k:Response(b'x'*65537))(self.messages)
    def test_bad_message_rejected(self):
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'key'}):
            with self.assertRaises(ModelTransportError): ChatCompletionsTransport(opener=lambda *a,**k:response())([{'role':'user','content':'x'}])
    def test_end_to_end_mocked_council_stays_blocked(self):
        def opener(req,timeout):
            role=json.loads(req.data)['messages'][0]['content']
            if 'structured research proposal' in role:
                return response('{"message":"No approved trade","proposal":{}}')
            return response()
        with patch.dict(os.environ,{'RUNLU_LLM_API_KEY':'key'}):
            adapter=JsonResearchAdapter(ChatCompletionsTransport(opener=opener))
            result=run_council(ResearchContext('CSU','a'*64,'evidence-1'),adapter)
        self.assertEqual(result['outcome']['status'],'BLOCKED')
        self.assertFalse(result['outcome']['order_submitted'])
    def test_timeout_range(self):
        for timeout in [0,61,True]:
            with self.assertRaises(ModelTransportError): ChatCompletionsTransport(timeout=timeout)

if __name__=='__main__': unittest.main()
