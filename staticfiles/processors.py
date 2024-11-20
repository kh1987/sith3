import json
import logging
import subprocess
from dataclasses import dataclass
from hashlib import sha1
from itertools import chain
from pathlib import Path
from typing import Iterable, Self

import rjsmin
import sass
from django.conf import settings

from sith.urls import api
from staticfiles.apps import BUNDLED_ROOT, GENERATED_ROOT


@dataclass
class JsBundlerManifestEntry:
    out: str
    src: str

    @classmethod
    def from_json_entry(cls, entry: dict[str, any]) -> list[Self]:
        ret = [
            cls(
                out=str(Path("bundled") / entry["file"]),
                src=str(Path(*Path(entry["src"]).parts[2:])),
            )
        ]
        for css in entry.get("css", []):
            path = Path("bundled") / css
            ret.append(
                cls(
                    out=str(path),
                    src=str(path.with_stem(entry["name"])),
                )
            )
        return ret


class JSBundlerManifest:
    def __init__(self, manifest: Path):
        with open(manifest, "r") as f:
            self._manifest = json.load(f)

        self._files = chain(
            *[
                JsBundlerManifestEntry.from_json_entry(value)
                for value in self._manifest.values()
                if value.get("isEntry", False)
            ]
        )
        self.mapping = {file.src: file.out for file in self._files}


class JSBundler:
    @staticmethod
    def compile():
        """Bundle js files with the javascript bundler for production."""
        process = subprocess.Popen(["npm", "run", "compile"])
        process.wait()
        if process.returncode:
            raise RuntimeError(f"Bundler failed with returncode {process.returncode}")

    @staticmethod
    def runserver() -> subprocess.Popen:
        """Bundle js files automatically in background when called in debug mode."""
        logging.getLogger("django").info("Running javascript bundling server")
        return subprocess.Popen(["npm", "run", "serve"])

    @staticmethod
    def get_manifest() -> JSBundlerManifest:
        return JSBundlerManifest(BUNDLED_ROOT / ".vite" / "manifest.json")

    @staticmethod
    def is_in_bundle(name: str | None) -> bool:
        if name is None:
            return False
        return name.startswith("bundled/")


class Scss:
    @dataclass
    class CompileArg:
        absolute: Path  # Absolute path to the file
        relative: Path  # Relative path inside the folder it has been collected

    @staticmethod
    def compile(files: CompileArg | Iterable[CompileArg]):
        """Compile scss files to css files."""
        # Generate files inside the generated folder
        # .css files respects the hierarchy in the static folder it was found
        # This converts arg.absolute -> generated/{arg.relative}.scss
        # Example:
        #   app/static/foo.scss          -> generated/foo.css
        #   app/static/bar/foo.scss      -> generated/bar/foo.css
        #   custom/location/bar/foo.scss -> generated/bar/foo.css
        if isinstance(files, Scss.CompileArg):
            files = [files]

        base_args = {"output_style": "compressed", "precision": settings.SASS_PRECISION}

        compiled_files = {
            file.relative.with_suffix(".css"): sass.compile(
                filename=str(file.absolute), **base_args
            )
            for file in files
        }
        for file, content in compiled_files.items():
            dest = GENERATED_ROOT / file
            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.write_text(content)


class JS:
    @staticmethod
    def minify():
        to_exec = [
            p
            for p in settings.STATIC_ROOT.rglob("*.js")
            if ".min" not in p.suffixes
            and (settings.STATIC_ROOT / "bundled") not in p.parents
        ]
        for path in to_exec:
            p = path.resolve()
            minified = rjsmin.jsmin(p.read_text())
            p.write_text(minified)
            logging.getLogger("main").info(f"Minified {path}")


class OpenApi:
    OPENAPI_DIR = GENERATED_ROOT / "openapi"

    @classmethod
    def compile(cls):
        """Compile a TS client for the sith API. Only generates it if it changed."""
        logging.getLogger("django").info("Compiling open api typescript client")
        out = cls.OPENAPI_DIR / "schema.json"
        cls.OPENAPI_DIR.mkdir(parents=True, exist_ok=True)

        old_hash = ""
        if out.exists():
            with open(out, "rb") as f:
                old_hash = sha1(f.read()).hexdigest()

        schema = api.get_openapi_schema()
        # Remove hash from operationIds
        # This is done for cache invalidation but this is too aggressive
        for path in schema["paths"].values():
            for action, desc in path.items():
                path[action]["operationId"] = "_".join(
                    desc["operationId"].split("_")[:-1]
                )
        schema = str(schema)

        if old_hash == sha1(schema.encode("utf-8")).hexdigest():
            logging.getLogger("django").info("✨ Api did not change, nothing to do ✨")
            return

        with open(out, "w") as f:
            _ = f.write(schema)

        subprocess.run(["npx", "openapi-ts"], check=True)
