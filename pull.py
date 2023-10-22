import sys
import os
import requests
from urllib.parse import urljoin

import config # Must have API_URL and IMAGES_PATH set



# Rework fetch_manifest - rename tag to sth like sig to also call it while working with manifest lists - use inside layer_from_manifest_list
# Maybe transform into PullCommand class



def generate_pull_token(image_name: str) -> str:
    request = requests.get(
        f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/{image_name}:pull")
    return request.json()['token']


def fetch_manifest(image_name: str, token: str, tag: str="latest") -> dict:
    url = urljoin(config.API_URL, f"{image_name}/manifests/{tag}")
    headers = {"Authorization": f"Bearer {token}"}
    manifest = requests.get(url=url, headers=headers)
    return manifest.json()


def is_manifest_list(manifest: dict[str, object]) -> bool:
    """
    Fetching manifests of certain images returns manifest list,
    which contains references to individual manifests of specific
    architectures instead of digests of individual image layers.
    This function differentiates between manifest and manifests list
    because manifest lists need to be handled differently
    """
    return "manifests" in manifest


def layers_from_manifest_list(token: str, image_name: str, image_digest: str):
    url = urljoin(config.API_URL, f"{image_name}/manifests/{image_digest}")
    url = f"https://registry.hub.docker.com/v2/library/{image_name}/manifests/{image_digest}"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.oci.image.manifest.v1+json"}

    request = requests.get(url=url, headers=headers)
    arch_manifest = request.json()
    return [layer["digest"] for layer in arch_manifest["layers"]]


def get_layer_digests(image_name: str, token: dict[str, object], manifest: str) -> list[str]:
    if not is_manifest_list(manifest):
        return [layer["blobSum"] for layer in manifest["fsLayers"]]

    # If manifest is manifest list
    for arch_manifest in manifest["manifests"]:
        if arch_manifest["platform"]["architecture"] == "amd64":
            return layers_from_manifest_list(token, image_name, arch_manifest["digest"])



def pull(image_name: str, tag: str="latest"):
    token = generate_pull_token(image_name)
    headers = {"Authorization": f"Bearer {token}"}
    manifest = fetch_manifest(image_name, token, tag)

    layers = get_layer_digests(image_name, token, manifest)
    unique_layers = set(layers)


    if not os.path.exists(config.IMAGES_PATH):
        os.makedirs(config.IMAGES_PATH)
    elif not os.path.isdir(config.IMAGES_PATH):
        print(f"{config.IMAGES_PATH} must be a directory", file=sys.stderr)

    # Separate to functions - maybe even block above
    with open(f"{config.IMAGES_PATH}/{image_name}-{tag}.tar", "ab") as output_file:
        for layer_digest in unique_layers:
            layer_chunk_request = requests.get(urljoin(config.API_URL, f"{image_name}/blobs/{layer_digest}"), headers=headers)

            if layer_chunk_request.status_code != 200:
                print("Request Error")
                sys.exit(1)
            
            for chunk in layer_chunk_request.iter_content(chunk_size=1024):
                output_file.write(chunk)


if __name__ == "__main__":
    pull("ubuntu")
