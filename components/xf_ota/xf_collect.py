import xf_build

srcs = ["*.c"]
incs = ["."]
reqs = [
    "xf_utils",
]

if xf_build.get_define("XF_OTA_ENABLE") == "y":
    xf_build.collect(srcs=srcs, inc_dirs=incs, requires=reqs)
