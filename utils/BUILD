#  Copyright 2020-2021 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted

load("@py_deps//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("@subpar//:subpar.bzl", "par_binary")

package(default_visibility = ["//visibility:public"])

py_library(
    name = "custom_collections",
    srcs = ["custom_collections.py"],
    deps = [
        requirement("fakeredis"),
        requirement("cachetools"),
    ],
)

py_library(
    name = "port_picker_lib",
    srcs = ["port_picker.py"],
)

par_binary(
    name = "port_picker",
    srcs = ["port_picker.py"],
)
