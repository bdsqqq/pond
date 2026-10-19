from pathlib import Path
import subprocess, os, json, tempfile, base64
root=Path(Path('/tmp/pond-127-validation-path').read_text()); repo=Path.cwd()
electron=repo/'apps/desktop/node_modules/electron/dist/Pond.app/Contents/MacOS/Electron'
phase=os.environ.get('POND_VALIDATION_PHASE','built')
cases=[('original','normal'),('original','denied'),('fixed','normal'),('fixed','denied'),('fixed','both')]
for variant,mode in cases:
 if os.environ.get('POND_VALIDATION_VARIANT') and variant != os.environ['POND_VALIDATION_VARIANT']: continue
 label=f'{phase}-{variant}-{mode}'; evidence=root/'evidence-final'/label
 evidence.mkdir(parents=True,exist_ok=True); sandbox=Path(tempfile.mkdtemp(prefix='p127-',dir='/tmp')).resolve(); (sandbox/'home').mkdir(); (evidence/'sandbox-path.txt').write_text(str(sandbox))
 (sandbox/'app-data').mkdir(); (sandbox/'app-data/secrets.json').write_text(json.dumps({'so.pond.desktop:ingest-token':'raw:'+base64.b64encode(b'isolated-smoke-token').decode()})); (sandbox/'app-data/secrets.json').chmod(0o600)
 env=os.environ.copy()
 for key in ['ELECTRON_RUN_AS_NODE','ELECTRON_RENDERER_URL','NODE_OPTIONS']: env.pop(key,None)
 env.update(HOME=str(sandbox/'home'),POND_SANDBOX=str(sandbox),POND_TEST_EVIDENCE=str(evidence),POND_TEST_LOG_MODE=mode,POND_TEST_EXPECT_FAILURE='1' if variant=='original' and mode=='denied' else '0',POND_TEST_PACKAGED='1' if phase=='packaged' else '0')
 app=root/variant/'apps/desktop'
 args=[str(app/'dist/mac-arm64/Pond.app/Contents/MacOS/Pond')] if phase=='packaged' else [str(electron),str(app)]
 with open(evidence/'process.log','w') as log:
  try: result=subprocess.run(args,cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=40)
  except subprocess.TimeoutExpired: print(label,'PROCESS TIMEOUT',flush=True); raise SystemExit(1)
 report=json.loads((evidence/'result.json').read_text()) if (evidence/'result.json').exists() else {}
 print(label,'exit',result.returncode,'ok',report.get('ok'),'observed',report.get('observed'),flush=True)
 if result.returncode or not report.get('ok'):
  print((evidence/'process.log').read_text()[-5000:],flush=True)
  raise SystemExit(1)
