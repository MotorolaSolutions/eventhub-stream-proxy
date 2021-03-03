# The MIT License (MIT)

# Copyright (C) 2020-2021 Motorola Solutions, Inc
# All rights reserved

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


load("@bazel_tools//tools/build_defs/pkg:pkg.bzl", "pkg_tar")
load("@io_bazel_rules_docker//container:container.bzl", "container_image", "container_push")
load("@io_bazel_rules_docker//contrib:passwd.bzl", "passwd_entry", "passwd_file")
load("@py_deps//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("@rules_python//python:defs.bzl", "py_test")
load("@io_bazel_rules_docker//lang:image.bzl", "app_layer")

package(default_visibility = ["//visibility:public"])

py_binary(
    name = "eventhub_stream_proxy",
    srcs = ["eventhub_stream_proxy_main.py"],
    main = "eventhub_stream_proxy_main.py",
    deps = [
        requirement("absl-py"),
        requirement("grpcio-health-checking"),
        requirement("grpcio"),
        requirement("protobuf"),
        requirement("azure-eventhub-checkpointstoreblob"),
        requirement("azure-eventhub"),
        requirement("pydevd-pycharm"),
        "//proto:event_py_proto",
        "//utils:port_picker_lib",
        ":eventhub_stream_proxy_impl",
    ]
)

py_library(
    name = "eventhub_stream_proxy_impl",
    srcs = ["eventhub_stream_proxy_impl.py"],
    deps = [
        requirement("grpcio"),
        requirement("protobuf"),
        "//proto:event_py_proto",
        "//utils:custom_collections",
    ]
)

py_binary(
    name = "example_client",
    srcs = ["example_client.py"],
    deps = [
        requirement("absl-py"),
        requirement("protobuf"),
        requirement("grpcio"),
        requirement("pydevd-pycharm"),
        "//proto:event_py_proto",
        "//utils:port_picker_lib",
    ]
)


py_test(
    name = "eventhub_stream_proxy_test",
    srcs = ["eventhub_stream_proxy_test.py"],
    deps = [
        requirement("grpcio"),
        requirement("mock"),
        requirement("protobuf"),
        "//proto:event_py_proto",
        ":eventhub_stream_proxy",
    ]
)

passwd_entry(
    username = "root",
    uid = 0,
    gid = 0,
    name = "root_user",
)

passwd_entry(
    username = "nonroot",
    info = "nonroot",
    uid = 1002,
    name = "nonroot_user",
)

passwd_file(
    name = "passwd",
    entries = [
        ":root_user",
        ":nonroot_user",
    ],
)

# Create a tar file containing the created passwd file
pkg_tar(
    name = "passwd_tar",
    srcs = [":passwd"],
    mode = "0o644",
    package_dir = "etc",
)

pkg_tar(
    name = "health_check_tar",
    srcs = ["@grpc_health_check_bin//file"],
    package_dir = "/bin",
)

container_image(
    name = "eventhub_stream_proxy_base_image",
    base = "@mycontainer//image",
    tars = [":passwd_tar", ":health_check_tar"],
    user = "nonroot",
)

app_layer(
    name = "eventhub_stream_proxy_image",
    base = ":eventhub_stream_proxy_base_image",
    entrypoint = ["/usr/local/bin/python"],
    binary = "eventhub_stream_proxy",
    args = ["--flagfile=/etc/config/eventhub_stream_proxy_flagfile"],
    create_empty_workspace_dir = True,
)
