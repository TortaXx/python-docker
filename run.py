import os
import tarfile
import sh
import ctypes
import ctypes.util
import unshare
import sys

import config

# libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
# libc.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_char_p]
# libc.unshare.argtypes = [ctypes.c_int]


# Assumes image `image_name` is already downloaded - doesn't pull it
def create_root(base_containers_dir: str, images_dir: str, image_name: str, image_tag: str) -> str:
    image_path = os.path.join(images_dir, f"{image_name}-{image_tag}.tar")
    container_path = os.path.join(base_containers_dir, f"{image_name}-{image_tag}")
    
    if not os.path.exists(container_path):
        os.makedirs(container_path)

    with tarfile.open(image_path, mode="w") as image_tar:
        image_tar.extractall(container_path)

    return container_path


def run_container(command: list[str], image_name: str, image_tag: str="latest"):

    new_root = create_root(config.CONTAINERS_PATH, config.IMAGES_PATH, image_name, image_tag)
    try:
        unshare.unshare(unshare.CLONE_NEWNS)
    except:
        print("Must be run with root privilleges", file=sys.stderr)
        sys.exit(1)
        # Further cleanup - is it neededd though?


    sh.mount("-tproc", '/proc', f"{new_root}/proc")
    sh.mount("--rbind", "/sys", f"{new_root}/sys")
    sh.mount("--rbind", "/dev", f"{new_root}/dev")

    os.chroot(new_root)
    os.chdir("/")

    os.execvp(command[0], command)




if __name__ == "__main__":
    # create_root(config.CONTAINERS_PATH, config.IMAGES_PATH, "ubuntu")
    run_container(["bash"], "ubuntu")


    
