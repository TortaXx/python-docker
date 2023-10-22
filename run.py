import os
import tarfile
import sh
import unshare
import sys
import shutil

import config
import pull



# Assumes image `image_name` is already downloaded - doesn't pull it
def create_root(base_containers_dir: str, images_dir: str, image_name: str, image_tag: str) -> str:
    image_path = os.path.join(images_dir, f"{image_name}-{image_tag}.tar") # Path where image .tar source is
    image_root = os.path.join(images_dir, f"{image_name}-{image_tag}", "rootfs") # Read only image root
    
    # Use some kind of id (UUID) instead of image_name-image_tag
    container_path = os.path.join(base_containers_dir, f"{image_name}-{image_tag}")

    
    container_root = os.path.join(container_path, "rootfs")
    container_upper_dir = os.path.join(container_path, "upper_dir")
    container_workdir = os.path.join(container_path, "workdir")

    if not os.path.exists(image_root):
        os.makedirs(image_root)

        with tarfile.open(image_path) as image_tar:
            image_tar.extractall(image_root) 

    for directory in [container_root, container_upper_dir, container_workdir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    sh.mount("-toverlay","overlay", f"-olowerdir={image_root},upperdir={container_upper_dir},workdir={container_workdir}", container_root)

    return container_root


def run_container(command: list[str], image_name: str, image_tag: str="latest"):
    new_root = create_root(config.CONTAINERS_PATH, config.IMAGES_PATH, image_name, image_tag)
    
    try:
        unshare.unshare(unshare.CLONE_NEWNS)
    except:
        print("Must be run with root privilleges", file=sys.stderr)
        sys.exit(1)
        # Further cleanup - is it neededd though?

    # Make root / private mountpoint so that it isnt polluted by mounts in the new namespace
    sh.mount("--make-rprivate", "/")

    sh.mount("-tproc", 'proc', f"{new_root}/proc")
    sh.mount("--bind", "/sys", f"{new_root}/sys") # Can be changed to mount instead of bind
    sh.mount("--bind", "/dev", f"{new_root}/dev") # not --rbind so that we dont pollute our mount namespace, same below
    sh.mount("-tdevpts", "devpts", f"{new_root}/dev/pts")
    # https://superuser.com/questions/165116/mount-dev-proc-sys-in-a-chroot-environment

    old_root = os.path.join(new_root, "old_root")
    if not os.path.exists(old_root):
        os.makedirs(old_root)

    sh.pivot_root(new_root, old_root)
    os.chdir("/")

    sh.umount("-R", "-l", "/old_root")
    os.rmdir("/old_root")


    os.execvp(command[0], command)




if __name__ == "__main__":
    pull.pull("ubuntu")
    # run_container(["bash", "--", "-c hostname"], "ubuntu")
    run_container(["bash"], "ubuntu")