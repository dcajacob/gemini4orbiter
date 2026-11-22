"""Publish the checked tag's package, resuming a partial draft on workflow retry."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def gh(*args, payload=None):
    return subprocess.check_output(["gh", *args], text=True,
                                   input=json.dumps(payload) if payload is not None else None).strip()


def publish(directory):
    repo = os.environ["GITHUB_REPOSITORY"]
    tag = os.environ["GITHUB_REF_NAME"]
    commit = os.environ["GITHUB_SHA"]
    if os.environ["GITHUB_EVENT_NAME"] != "push" or os.environ["GITHUB_REF_TYPE"] != "tag" or not tag.startswith("gemini-viii-linux-opengl-"):
        raise ValueError("Publication requires a Gemini VIII Linux OpenGL tag push")
    api = f"repos/{repo}"
    def verify_tag():
        if gh("api", f"{api}/commits/{tag}", "--jq", ".sha") != commit:
            raise ValueError("Tag has moved since verification")
    verify_tag()
    notes_file = directory / "release-notes.md"
    marker = f"<!-- Gemini release workflow {os.environ['GITHUB_RUN_ID']} {commit} -->"
    body = notes_file.read_text() + "\n" + marker
    archive = "Gemini-VIII-Linux-OpenGL-x86_64.tar.zst"
    parts = sorted(directory.glob(archive + ".part[0-9][0-9]"))
    if not parts:
        raise ValueError("Missing split archive")
    files = parts + [directory / name for name in (archive + ".sha256", "SHA256SUMS.parts", "LAUNCH.md", "launcher-checks.json")]
    expected = {}
    for file in files:
        with file.open("rb") as stream:
            expected[file.name] = "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()

    # The list endpoint includes unpublished drafts for the release token.
    refs = gh("api", "--paginate", f"{api}/releases?per_page=100", "--jq", '.[] | [.tag_name, .id] | @tsv')
    releases = dict(line.split("\t") for line in refs.splitlines())
    if tag in releases:
        release = json.loads(gh("api", f"{api}/releases/{releases[tag]}"))
    else:
        release = json.loads(gh("api", f"{api}/releases", "--method", "POST", "--input", "-", payload={
            "tag_name": tag, "target_commitish": commit, "name": f"Gemini VIII Linux OpenGL ({tag})",
            "body": body, "draft": True}))
    endpoint = f"{api}/releases/{release['id']}"

    def remote_digests(metadata):
        return {a["name"]: a.get("digest") if a["state"] == "uploaded" else None for a in metadata["assets"]}

    remote = remote_digests(release)
    if not release["draft"]:
        if remote != expected:
            raise ValueError("A different public release already exists for this tag")
        print(release["html_url"])
        return
    if marker not in release["body"] or remote.keys() - expected.keys():
        raise ValueError("An unrelated draft exists for this tag")
    for file in files:
        if remote.get(file.name) != expected[file.name]:
            gh("release", "upload", tag, str(file), "--repo", repo, "--clobber")
    if remote_digests(json.loads(gh("api", endpoint))) != expected:
        raise ValueError("Uploaded release assets differ from the verified package")
    verify_tag()
    published = json.loads(gh("api", endpoint, "--method", "PATCH", "--input", "-",
                              payload={"body": body, "draft": False}))
    if published["draft"]:
        raise RuntimeError("Release is still a draft")
    print(published["html_url"])


if __name__ == "__main__":
    publish(Path(sys.argv[1]))
