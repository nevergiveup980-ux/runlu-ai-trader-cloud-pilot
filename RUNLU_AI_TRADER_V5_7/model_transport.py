"""Optional OpenAI-compatible chat completion transport for research ONLY.

No requests occur on import. No broker/order endpoints exist. Credentials are read
from the environment at call time and are never included in errors or audit logs.
"""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

class ModelTransportError(ValueError):
    pass

class ChatCompletionsTransport:
    def __init__(self, *, endpoint='https://api.openai.com/v1/chat/completions', model='gpt-4.1-mini',
                 api_key_env='RUNLU_LLM_API_KEY', timeout=20, opener=None):
        parsed = urlparse(endpoint)
        if (parsed.scheme != 'https' or parsed.hostname not in {'api.openai.com'} or
                parsed.username or parsed.password or parsed.query or parsed.fragment or
                parsed.path != '/v1/chat/completions' or parsed.port not in (None,443)):
            raise ModelTransportError('Endpoint must be the approved HTTPS chat-completions endpoint')
        if not isinstance(model,str) or not model or len(model)>100 or any(c.isspace() for c in model):
            raise ModelTransportError('Invalid model name')
        if not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not 1 <= timeout <= 60:
            raise ModelTransportError('Timeout must be 1..60 seconds')
        self.endpoint=endpoint; self.model=model; self.api_key_env=api_key_env
        self.timeout=timeout; self.opener=opener or urlopen

    def __call__(self, messages):
        if not isinstance(messages,list) or len(messages)!=2 or [m.get('role') for m in messages] != ['system','user']:
            raise ModelTransportError('Expected system and user research messages')
        for message in messages:
            if not isinstance(message.get('content'),str) or len(message['content'])>12000:
                raise ModelTransportError('Invalid message content')
        key=os.environ.get(self.api_key_env,'')
        if not key or any(ch in key for ch in '\r\n'):
            raise ModelTransportError('Model API key is missing or invalid')
        body=json.dumps({'model':self.model,'messages':messages,'temperature':0,
                         'response_format':{'type':'json_object'},'max_tokens':900},separators=(',',':')).encode()
        request=Request(self.endpoint,data=body,headers={'Authorization':'Bearer '+key,
                    'Content-Type':'application/json'},method='POST')
        try:
            with self.opener(request,timeout=self.timeout) as response:
                raw=response.read(65537)
        except (HTTPError,URLError,TimeoutError,OSError) as exc:
            raise ModelTransportError('Model request failed; details suppressed') from None
        if len(raw)>65536: raise ModelTransportError('Model response exceeds size limit')
        try:
            obj=json.loads(raw)
            choices=obj['choices']
            if not isinstance(choices,list) or len(choices)!=1: raise ValueError('choices')
            choice=choices[0]
            if choice.get('finish_reason')!='stop': raise ValueError('incomplete')
            content=choice['message']['content']
            if not isinstance(content,str): raise ValueError('content')
            return content
        except (ValueError,KeyError,TypeError,IndexError):
            raise ModelTransportError('Invalid or incomplete model response') from None
