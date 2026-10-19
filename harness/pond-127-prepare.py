import os, pathlib, subprocess, tempfile, tarfile, io, shutil, json, hashlib
repo=pathlib.Path.cwd()
root=pathlib.Path(tempfile.mkdtemp(prefix='pond-127-validation-'))
pathlib.Path('/tmp/pond-127-validation-path').write_text(str(root))
archive=subprocess.check_output(['git','archive','HEAD'],cwd=repo)
changed=['apps/desktop/src/main/index.ts','apps/desktop/src/main/paths.ts','apps/desktop/src/main/logging.ts','apps/desktop/src/main/logging.test.ts']
manifest={'base':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'platform':subprocess.check_output(['uname','-a'],text=True).strip(),'files':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in changed},'instrumentation':'same observer and permission fixture inserted after sandbox setup in both snapshots'}
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
(root/'fix.diff').write_bytes(subprocess.check_output(['git','diff','--','apps/desktop/src/main/index.ts','apps/desktop/src/main/paths.ts']))
for variant in ['original','fixed']:
    checkout=root/variant
    checkout.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar: tar.extractall(checkout)
    if variant=='fixed':
        for p in changed: shutil.copy2(repo/p,checkout/p)
    for p in [pathlib.Path('node_modules')]+[x.relative_to(repo) for group in ['apps','packages'] for x in (repo/group).glob('*/node_modules')]:
        if (repo/p).exists(): (checkout/p).symlink_to(repo/p,target_is_directory=True)
    # Packaging inputs were already built from the same unchanged source.
    for p in ['apps/desktop/resources','apps/desktop/build','apps/extension/.output']:
        target=checkout/p
        if target.exists(): shutil.rmtree(target)
        shutil.copytree(repo/p,target)
    entry=checkout/'apps/desktop/src/main/index.ts'
    source=entry.read_text()
    needle='if (process.platform === "darwin") {\n  app.setAboutPanelOptions'
    assert source.count(needle)==1
    source='import { prepareLoggingFailure } from "./logging-startup-smoke";\n'+source
    source=source.replace(needle,'prepareLoggingFailure();\n\n'+needle)
    entry.write_text(source)
print(root)
