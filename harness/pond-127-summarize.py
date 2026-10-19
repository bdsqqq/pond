from pathlib import Path
import json, hashlib, shutil, subprocess
r=Path(Path('/tmp/pond-127-validation-path').read_text()); repo=Path.cwd()
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return h.hexdigest()
m=json.loads((r/'manifest.json').read_text())
assert all(sha(repo/p)==h for p,h in m['files'].items())
for v in ['original','fixed']:
 entry=r/v/'apps/desktop/src/main/index.ts'
 source=entry.read_text().replace('import { prepareLoggingFailure } from "./logging-startup-smoke";\n','',1).replace('prepareLoggingFailure();\n\n','',1)
 expected=subprocess.check_output(['git','show','HEAD:apps/desktop/src/main/index.ts'],text=True) if v=='original' else (repo/'apps/desktop/src/main/index.ts').read_text()
 assert source==expected
for name in ['pond-127-prepare.py','pond-127-run.py','pond-127-package.py','pond-127-startup-fixture.ts','pond-127-summarize.py']:
 shutil.copy2(Path('/tmp')/name,r/name)
m['instrumentation_sha256']=sha(r/'pond-127-startup-fixture.ts')
m['packaging']={'electron':'44.4.0','arch':'arm64','signing':False,'notarization':False,'asar':True,'binaryVerifier':'scripts/verify-binaries.cjs passed','nativeRebuild':False,'nativeHost':'compiled from each snapshot with scripts/build-native-host.mjs'}
m['artifact_sha256']={v:{'main':sha(r/v/'apps/desktop/out/main/index.js'),'asar':sha(r/v/'apps/desktop/dist/mac-arm64/Pond.app/Contents/Resources/app.asar')} for v in ['original','fixed']}
(r/'manifest.json').write_text(json.dumps(m,indent=2))
cases=[]
for phase in ['built','packaged']:
 for v,mode in [('original','normal'),('original','denied'),('fixed','normal'),('fixed','denied'),('fixed','both')]:
  label=f'{phase}-{v}-{mode}';d=r/'evidence-final'/label;result=json.loads((d/'result.json').read_text());assert result['ok'];assert result['isPackaged']==(phase=='packaged')
  assert result['expectFailure']==(v=='original' and mode=='denied')
  if not result['expectFailure']: assert result['state']['bootDismissed']
  cases.append({'case':label,'assertionsPassed':True,'expectedStartup':'rejection before window' if result['expectFailure'] else 'visible app after boot cover dismissed, real preload queries succeed','result':str(d/'result.json'),'fixture':str(d/'fixture.json'),'screenshot':str(d/'window.png') if not result['expectFailure'] else None})
summary={'conclusion':'the reproduced permission-denied logs startup failure occurs before the fix and is absent with the fix in built and unsigned packaged macOS arm64 apps','baseRevision':m['base'],'manifest':str(r/'manifest.json'),'cases':cases,'checksReused':['pnpm check','pnpm build'],'proofBoundary':['identical test-only observer and real filesystem permission fixture inserted after sandbox setup in disposable copies','actual Electron main, preload, renderer and native database code executed','synthetic empty libraries and fixture ingest token; personal library not opened','unsigned .app bundles launched directly; DMG installation, notarization and Gatekeeper not exercised'],'screenshotsInspected':True,'sourceWorkingTreeUnchangedByValidation':True,'visualInspection':{'accepted':['built-original-normal','built-fixed-normal','built-fixed-denied','built-fixed-both','packaged-original-normal','packaged-fixed-denied','packaged-fixed-both'],'inconclusive':{'packaged-fixed-normal':'capture still shows startup cover despite bootDismissed DOM assertion; cause unverified. Not used as visual proof. Both targeted permission-failure captures show usable UI.'}}}
(r/'summary.json').write_text(json.dumps(summary,indent=2));print(r/'summary.json')
