from pathlib import Path
import subprocess, os
root=Path(Path('/tmp/pond-127-validation-path').read_text()); repo=Path.cwd()
env=os.environ.copy()
for key in ['CSC_LINK','CSC_KEY_PASSWORD','CSC_NAME','CSC_IDENTITY','APPLE_ID','APPLE_APP_SPECIFIC_PASSWORD','APPLE_TEAM_ID','APPLE_API_KEY','APPLE_API_KEY_ID','APPLE_API_ISSUER','ELECTRON_RUN_AS_NODE','NODE_OPTIONS']:
 env.pop(key,None)
env['CSC_IDENTITY_AUTO_DISCOVERY']='false'
env['npm_config_user_agent']='pnpm/11.27.0'
for variant in ['original','fixed']:
 app=root/variant/'apps/desktop'
 with open(root/(variant+'-package.log'),'w') as log:
  native=subprocess.run(['node','scripts/build-native-host.mjs'],cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=30)
  if native.returncode: raise SystemExit(native.returncode)
  result=subprocess.run([str(repo/'apps/desktop/node_modules/.bin/electron-builder'),'--mac','--dir','--arm64','--publish','never','--config.npmRebuild=false','--config.mac.notarize=false','--config.mac.identity=null'],cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 print(variant,'package',result.returncode,flush=True)
 if result.returncode:
  print((root/(variant+'-package.log')).read_text()[-4000:],flush=True)
  raise SystemExit(result.returncode)
