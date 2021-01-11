#  Copyright 2021 Motorola Solutions, Inc.
#  All Rights Reserved.
#  Motorola Solutions Confidential Restricted

# On Ubuntu:
# sudo apt install python3-distutils

# Generic rules
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")

http_archive(
    name = "rules_python",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.1.0/rules_python-0.1.0.tar.gz",
    sha256 = "b6d46438523a3ec0f3cead544190ee13223a52f6a6765a29eae7b7cc24cc83a0",
)
load("@rules_python//python:pip.bzl", "pip_repositories")
pip_repositories()


load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "rules_proto_grpc",
    urls = ["https://github.com/rules-proto-grpc/rules_proto_grpc/archive/2.0.0.tar.gz"],
    sha256 = "d771584bbff98698e7cb3cb31c132ee206a972569f4dc8b65acbdd934d156b33",
    strip_prefix = "rules_proto_grpc-2.0.0",
)

load("@rules_proto_grpc//:repositories.bzl", "rules_proto_grpc_toolchains", "rules_proto_grpc_repos")
rules_proto_grpc_toolchains()
rules_proto_grpc_repos()

load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies", "rules_proto_toolchains")
rules_proto_dependencies()
rules_proto_toolchains()

# For Python
load("@rules_proto_grpc//python:repositories.bzl", rules_proto_grpc_python_repos="python_repos")
rules_proto_grpc_python_repos()

load("@com_github_grpc_grpc//bazel:grpc_deps.bzl", "grpc_deps")
grpc_deps()

load("@rules_python//python:repositories.bzl", "py_repositories")
py_repositories()

load("@rules_python//python:pip.bzl", "pip_install")
pip_install(
    name = "rules_proto_grpc_py3_deps",
    python_interpreter = "python3",
    requirements = "@rules_proto_grpc//python:requirements.txt",
)

http_archive(
    name = "io_bazel_rules_docker",
    # patches = ["//:rules_docker.pr1650.patch"],
    sha256 = "1698624e878b0607052ae6131aa216d45ebb63871ec497f26c67455b34119c80",
    strip_prefix = "rules_docker-0.15.0",
    urls = ["https://github.com/bazelbuild/rules_docker/releases/download/v0.15.0/rules_docker-v0.15.0.tar.gz"],
)

load(
    "@io_bazel_rules_docker//repositories:repositories.bzl",
    container_repositories="repositories",
)
container_repositories()

load("@io_bazel_rules_docker//repositories:deps.bzl", container_deps="deps")
container_deps()

load(
    "@io_bazel_rules_docker//container:container.bzl",
    "container_pull",
)

container_pull(
  name = "java_base",
  registry = "gcr.io",
  repository = "distroless/java",
  digest = "sha256:deadbeef",
)

container_repositories()

load(
    "@io_bazel_rules_docker//python3:image.bzl",
    _py_image_repos = "repositories",
)
_py_image_repos()

http_archive(
    name = "rules_proto",
    sha256 = "602e7161d9195e50246177e7c55b2f39950a9cf7366f74ed5f22fd45750cd208",
    strip_prefix = "rules_proto-97d8af4dc474595af3900dd85cb3a29ad28cc313",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_proto/archive/97d8af4dc474595af3900dd85cb3a29ad28cc313.tar.gz",
        "https://github.com/bazelbuild/rules_proto/archive/97d8af4dc474595af3900dd85cb3a29ad28cc313.tar.gz",
    ],
)
load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies", "rules_proto_toolchains")
rules_proto_dependencies()
rules_proto_toolchains()


container_pull(
    name = "mycontainer",
    registry ="index.docker.io",
    repository = "library/python",
    tag = "3.8-slim-buster",
    digest = "sha256:87e7a5744fa7df0b441abebf63c0d27c86fd1ceb109e849ea9ccd82cf27abb65",
)

# Custom pip install
rules_python_external_version = "a6c756df528d4e6034a9f5ddebfe297910134092"

http_archive(
    name = "rules_python_external",
    sha256 = "4577e9462bf1cda6786c636a886054afa6e7eb0b940ba9c4462c5cd73fecd84f",
    strip_prefix = "rules_python_external-{version}".format(version = rules_python_external_version),
    url = "https://github.com/dillon-giacoppo/rules_python_external/archive/{version}.zip".format(version = rules_python_external_version),
)

# Install the rule dependencies
load("@rules_python_external//:repositories.bzl", "rules_python_external_dependencies")
rules_python_external_dependencies()

load("@rules_python_external//:defs.bzl", "pip_install")
pip_install(
    name = "py_deps",
    requirements = "//:requirements.txt",
)

# Health check command-line
http_file(
    name = "grpc_health_check_bin",
    downloaded_file_path = "grpc_health_probe",
    sha256 = "fc7e9f992f882c6f55e549c1038a31fc5ed47880bf4b91601cea64f93ef7f442",
    urls = ["https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.3.2/grpc_health_probe-linux-amd64"],
)
