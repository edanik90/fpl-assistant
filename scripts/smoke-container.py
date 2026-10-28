"""Exercise the shipped image with a disposable volume and no external networking.

Uses only the host's Python standard library and Docker CLI. Never touches the
normal Compose container or its saved app_data volume.
"""
import argparse
import json
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="fpl-assistant:local")
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--platform")
    args = parser.parse_args()
    identity = "fpl-smoke-" + uuid.uuid4().hex[:12]
    container, volume = identity, identity + "-data"

    def docker(*command, check=True):
        return subprocess.run(
            [args.docker, *command], capture_output=True, text=True,
            timeout=120, check=check,
        )

    def execute(code):
        return docker("exec", container, "/usr/bin/python3", "-c", code).stdout

    def start():
        options = ["--platform", args.platform] if args.platform else []
        docker(
            "run", "--detach", "--name", container, *options,
            "--network", "none", "--read-only", "--tmpfs", "/tmp",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--mount", f"type=volume,source={volume},target=/data", args.image,
        )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                health = json.loads(execute(
                    "import json,urllib.request; "
                    "print(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2).read().decode())"
                ))
                assert health["status"] == "ok"
                return
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                time.sleep(0.5)
        raise RuntimeError("Runtime did not become healthy within 45 seconds")

    try:
        docker("volume", "create", volume)
        start()
        inventory = json.loads(execute(
            "import glob,json,os,pathlib,shutil,sqlite3,sys; "
            "import greenlet,pydantic_core; "
            "db=sqlite3.connect(':memory:'); assert db.execute('select 1').fetchone()==(1,); "
            "names=sorted({line.split(': ',1)[1] for p in glob.glob('/var/lib/dpkg/status.d/*') "
            "for line in pathlib.Path(p).read_text(errors='replace').splitlines() if line.startswith('Package: ')}); "
            "tools={name:shutil.which(name) for name in ['sh','bash','apt','dpkg','pip','mount','nsenter','infocmp','perl']}; "
            "assert os.getuid()==10001; assert sys.version_info[:2]==(3,13); "
            "assert not any(tools.values()), tools; "
            "assert not any(name in names for name in ['bsdutils','util-linux','util-linux-extra','mount','login','perl-base','ncurses-bin','libncursesw6','libtinfo6','libuuid1','systemd','libsystemd0','libudev1','libacl1','libpython3.13-minimal','libpython3.13-stdlib']), names; "
            "print(json.dumps({'uid':os.getuid(),'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'packages':names,'absent_tools':tools}))"
        ))
        print(json.dumps({"runtime_inventory": inventory}), flush=True)
        result = json.loads(execute(
            "import json,re,urllib.request; "
            "base='http://127.0.0.1:8000'; "
            "data=json.load(urllib.request.urlopen(base+'/api/overview')); "
            "assert len(data['picks'])==15 and len(data['players'])==20; "
            "html=urllib.request.urlopen(base+'/').read().decode(); assert 'FPL Assistant' in html; "
            "assets=re.findall(r'(?:src|href)=\"(/assets/[^\"]+)\"',html); assert len(assets)>=2; "
            "assert all(urllib.request.urlopen(base+p).status==200 for p in assets); "
            "payload=json.dumps({'name':'Runtime smoke test','notes':'Survives container replacement.'}).encode(); "
            "request=urllib.request.Request(base+'/api/workspace',data=payload,method='PUT',headers={'Content-Type':'application/json','Origin':base}); "
            "saved=json.load(urllib.request.urlopen(request)); "
            "print(json.dumps({'workspace':saved,'snapshot':data['snapshot']}))"
        ))
        docker("stop", "--time", "10", container)
        docker("rm", container)
        start()
        persisted = json.loads(execute(
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/overview').read().decode())"
        ))
        assert persisted["workspace"] == result["workspace"], "Workspace changed during replacement"
        assert persisted["snapshot"] == result["snapshot"], "Demo seed changed during replacement"
        print("PASS: startup, migrations, native modules, static assets, writes and persistence after container replacement.")
    except Exception:
        print(docker("logs", container, check=False).stdout)
        raise
    finally:
        docker("rm", "--force", container, check=False)
        docker("volume", "rm", volume, check=False)


if __name__ == "__main__":
    main()
