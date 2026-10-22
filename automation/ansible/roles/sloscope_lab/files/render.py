#!/usr/bin/env python3
"""Render namespace-scoped lab resources; never creates a namespace, Secret, Route or RBAC."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
MANAGED={'app.kubernetes.io/part-of':'sloscope-lab','app.kubernetes.io/managed-by':'sloscope-lab'}


def render(namespace,engine_image,prometheus_image,model_secret='sloscope-model',storage_class='',lookback='5m',scenario_phase='baseline',include_engine=True,require_model=True):
    for field,value in [('namespace',namespace),('model_secret',model_secret)]:
        if len(value)>63 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?',value):
            raise ValueError(field+' must be a Kubernetes DNS label')
    for field,value in [('engine_image',engine_image),('prometheus_image',prometheus_image)]:
        if not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}',value):
            raise ValueError(field+' requires an immutable registry/repository@sha256 digest')
    if lookback not in ('5m','10m','15m','30m','1h'):
        raise ValueError('lookback must be an explicitly supported lab interval: 5m,10m,15m,30m,1h')
    if scenario_phase not in ('baseline','regression','recovery'):
        raise ValueError('Unknown scenario phase')
    if storage_class and not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',storage_class):
        raise ValueError('Invalid storage class name')
    objects=[]
    def resource(kind,name,spec=None,data=None):
        obj={'apiVersion':'v1','kind':kind,'metadata':{'name':name,'namespace':namespace,'labels':dict(MANAGED)}}
        if spec is not None:obj['spec']=spec
        if data is not None:obj['data']=data
        objects.append(obj)
        return obj
    scripts_data={name:(ROOT/name).read_text() for name in ('checkout.py','traffic.py','validate_live.py','classify_live.py')}
    scripts_sha=hashlib.sha256(json.dumps(scripts_data,sort_keys=True).encode()).hexdigest()
    resource('ConfigMap','sloscope-lab-scripts',data=scripts_data)
    resource('ConfigMap','sloscope-scenario',data={'phase':scenario_phase})
    prom_config='''global:
  scrape_interval: 10s
  evaluation_interval: 10s
rule_files:
  - /etc/prometheus/qualification-rules.yml
scrape_configs:
  - job_name: checkout-lab
    honor_labels: true
    static_configs:
      - targets: ['checkout-api:8081']
'''
    prom_data={'prometheus.yml':prom_config,'qualification-rules.yml':'groups: []\n'}
    prom_sha=hashlib.sha256(json.dumps(prom_data,sort_keys=True).encode()).hexdigest()
    resource('ConfigMap','sloscope-prometheus',data=prom_data)
    pvc={'accessModes':['ReadWriteOnce'],'resources':{'requests':{'storage':'1Gi'}}}
    if storage_class:pvc['storageClassName']=storage_class
    if include_engine:
        resource('PersistentVolumeClaim','sloscope-artifacts',spec=pvc)
    security={'allowPrivilegeEscalation':False,'runAsNonRoot':True,'readOnlyRootFilesystem':True,'capabilities':{'drop':['ALL']}}
    def deployment(name,image,command=None,args=None,port=None,env=None,mounts=None,volumes=None):
        labels={**MANAGED,'app.kubernetes.io/name':name,'app':name}
        container={'name':name,'image':image,'imagePullPolicy':'IfNotPresent','securityContext':security,
                   'resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'1','memory':'512Mi'}}}
        if command:container['command']=command
        if args:container['args']=args
        if env:container['env']=env
        if mounts:container['volumeMounts']=mounts
        if port:
            container['ports']=[{'containerPort':port,'name':'http'}]
            path='/-/ready' if name=='sloscope-prometheus' else '/health'
            container['readinessProbe']={'httpGet':{'path':path,'port':'http'},'periodSeconds':5,'initialDelaySeconds':3}
            container['livenessProbe']={'httpGet':{'path':path,'port':'http'},'periodSeconds':15,'initialDelaySeconds':10}
        annotations={'sloscope-lab/prometheus-config-sha256':prom_sha} if name=='sloscope-prometheus' else {'sloscope-lab/scripts-sha256':scripts_sha}
        obj=resource('Deployment',name,spec={'replicas':1,'selector':{'matchLabels':{'app.kubernetes.io/name':name}},
            'strategy':{'type':'Recreate'},'template':{'metadata':{'labels':labels,'annotations':annotations},'spec':{
                'automountServiceAccountToken':False,'securityContext':{'runAsNonRoot':True,'seccompProfile':{'type':'RuntimeDefault'}},
                'containers':[container],'volumes':volumes or []}}})
        obj['apiVersion']='apps/v1'
    scripts={'name':'scripts','configMap':{'name':'sloscope-lab-scripts'}}
    scriptmount={'name':'scripts','mountPath':'/opt/sloscope-lab','readOnly':True}
    temp={'name':'tmp','emptyDir':{}}
    tempmount={'name':'tmp','mountPath':'/tmp'}
    deployment('checkout-api',engine_image,['python','/opt/sloscope-lab/checkout.py'],port=8081,
        env=[{'name':'POD_NAMESPACE','valueFrom':{'fieldRef':{'fieldPath':'metadata.namespace'}}},{'name':'PYTHONDONTWRITEBYTECODE','value':'1'}],
        mounts=[scriptmount,{'name':'scenario','mountPath':'/scenario','readOnly':True},tempmount],
        volumes=[scripts,{'name':'scenario','configMap':{'name':'sloscope-scenario'}},temp])
    deployment('checkout-traffic',engine_image,['python','/opt/sloscope-lab/traffic.py'],
        env=[{'name':'PYTHONDONTWRITEBYTECODE','value':'1'}],mounts=[scriptmount,tempmount],volumes=[scripts,temp])
    deployment('sloscope-prometheus',prometheus_image,args=['--config.file=/etc/prometheus/prometheus.yml','--storage.tsdb.path=/prometheus',
        '--storage.tsdb.retention.time=2h','--web.listen-address=0.0.0.0:9090'],port=9090,
        mounts=[{'name':'config','mountPath':'/etc/prometheus','readOnly':True},{'name':'data','mountPath':'/prometheus'},tempmount],
        volumes=[{'name':'config','configMap':{'name':'sloscope-prometheus'}},{'name':'data','emptyDir':{}},temp])
    engine_env=[{'name':'PROM_URL','value':'http://sloscope-prometheus:9090'},
        {'name':'SLOSCOPE_LOOKBACK','value':lookback},{'name':'SLOSCOPE_STORE_DIR','value':'/artifacts'},
        {'name':'SLOSCOPE_SEED_DEMO','value':'false'},{'name':'SLOSCOPE_REQUIRE_MODEL','value':str(require_model).lower()},
        {'name':'PYTHONDONTWRITEBYTECODE','value':'1'}]
    for key in ('LLM_BASE_URL','LLM_API_KEY','LLM_MODEL'):
        engine_env.append({'name':key,'valueFrom':{'secretKeyRef':{'name':model_secret,'key':key,'optional':not require_model}}})
    if include_engine:
        deployment('sloscope',engine_image,port=8080,env=engine_env,mounts=[scriptmount,{'name':'artifacts','mountPath':'/artifacts'},tempmount],
            volumes=[scripts,{'name':'artifacts','persistentVolumeClaim':{'claimName':'sloscope-artifacts'}},temp])
    services=[('checkout-api',8081),('sloscope-prometheus',9090)]
    if include_engine:services.append(('sloscope',8080))
    for name,port in services:
        resource('Service',name,spec={'type':'ClusterIP','selector':{'app.kubernetes.io/name':name},'ports':[{'name':'http','port':port,'targetPort':'http'}]})
    policy=resource('NetworkPolicy','sloscope-lab-internal',spec={'podSelector':{'matchLabels':{'app.kubernetes.io/part-of':'sloscope-lab'}},
        'policyTypes':['Ingress'],'ingress':[{'from':[{'podSelector':{'matchLabels':{'app.kubernetes.io/part-of':'sloscope-lab'}}}]}]})
    policy['apiVersion']='networking.k8s.io/v1'
    return {'apiVersion':'v1','kind':'List','items':objects}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace',required=True)
    parser.add_argument('--engine-image',required=True)
    parser.add_argument('--prometheus-image',required=True)
    parser.add_argument('--model-secret',default='sloscope-model')
    parser.add_argument('--storage-class',default='')
    parser.add_argument('--lookback',default='5m')
    parser.add_argument('--scenario-phase',default='baseline')
    parser.add_argument('--include-engine',choices=['true','false'],default='true',help='false starts only controlled telemetry while a dedicated model Secret is provisioned')
    parser.add_argument('--require-model',choices=['true','false'],default='true',help='false is measurement-only: missing dedicated model Secret does not block engine startup')
    args=parser.parse_args()
    print(json.dumps(render(args.namespace,args.engine_image,args.prometheus_image,args.model_secret,args.storage_class,args.lookback,args.scenario_phase,args.include_engine=='true',args.require_model=='true'),indent=2))

if __name__=='__main__':
    main()
