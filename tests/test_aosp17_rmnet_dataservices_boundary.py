#!/usr/bin/env python3
"""PE-Reborn stage197: Qualcomm Data Services archive, RMNET kernel/UAPI boundary.

Checks are source/manifest-level. No modem, device HAL, AOSP17 Soong build,
kernel, or physical target is executed. Original Qualcomm sources stay intact.
"""
from pathlib import Path
import os
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "dfc2ec0112353afdb6db99db8bae7328b42e44f6"
ORIGINAL_TREE = "c2f2692c171be369f0b90248ec457dc50e6ea290"
LEGACY_PATH = "vendor/qcom/opensource/dataservices"
LEGACY_NAME = "vendor_qcom_opensource_dataservices"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def git_entry(ref, path):
    result = git("ls-tree", ref, "--", path)
    if not result:
        raise AssertionError("Git entry missing " + path)
    left, returned = result.split("\t", 1)
    if returned != path:
        raise AssertionError("Unexpected Git path " + returned)
    mode, kind, sha = left.split()
    return mode, kind, sha


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def pin(key):
    file = os.environ.get(key)
    if not file or not Path(file).is_file():
        raise AssertionError("Missing immutable text input " + key)
    return Path(file).read_text(encoding="utf-8")


class QualcommRmnetDataservicesAudit(unittest.TestCase):
    def test_archive_history_preserved(self):
        x = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", ARCHIVE, "HEAD"],
            capture_output=True, text=True,
        )
        self.assertEqual(x.returncode, 0, x.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE + "^{tree}"), ORIGINAL_TREE)

    def test_original_source_subtrees_unchanged(self):
        fixtures = {
            "Android.bp": ("100644", "blob", "9515b25732000716036b754fa6b2a23444c3d9a3"),
            "dataservices_vendor_product.mk": ("100644", "blob",
                                               "e81b5dc9c47b6cfe027fa386c2472bfb9959c361"),
            "Makefile.am": ("100755", "blob", "f2ad6f985d4ba100a2090a97777c921ef9fa9838"),
            "configure.ac": ("100644", "blob", "b6901eeddc3ac89e5349be6639716db70c1b47c8"),
            "rmnetctl": ("040000", "tree", "7de98a2eddfbad2ad2e4268442678769bab61b70"),
            "datatop": ("040000", "tree", "f43813b9d332bd21d19387ecf30fd5c31d9d8dd7"),
        }
        for path, value in fixtures.items():
            with self.subTest(path=path):
                self.assertEqual(git_entry("HEAD", path), value)
                self.assertEqual(git_entry(ARCHIVE, path), value)

    def test_root_soong_namespace_does_not_install_modem_stack(self):
        self.assertEqual(read("Android.bp").strip(),
                         "soong_namespace {\n}")
        self.assertFalse((ROOT / "AndroidProducts.mk").exists())
        self.assertFalse((ROOT / "device.mk").exists())
        self.assertFalse((ROOT / "BoardConfig.mk").exists())
        self.assertFalse(any(ROOT.rglob("*.aidl")))
        # This is the RMNET control library/CLI, not complete telephony or
        # Qualcomm data service binder/HAL implementation.

    def test_historic_rmnet_soong_modules_have_external_kernel_headers(self):
        bp = read("rmnetctl/Android.bp")
        for item in (
            'name: "rmnetctl_cc_defaults"',
            'config_namespace: "rmnetctl"',
            '"old_rmnet_data"',
            'name: "librmnetctl_headers"',
            'name: "librmnetctl_defaults"',
            'name: "librmnetctl"',
            'name: "rmnetcli"',
            '"qti_kernel_headers"',
            '"device_kernel_headers"',
        ):
            with self.subTest(item=item):
                self.assertIn(item, bp)
        self.assertIn('cflags: ["-DUSE_OLD_RMNET_DATA"]', bp)
        names = re.findall(r'\bname:\s*"([^"]+)"', bp)
        self.assertEqual(names, [
            "rmnetctl_cc_defaults", "librmnetctl_headers",
            "librmnetctl_defaults", "librmnetctl", "rmnetcli",
        ])
        # Header providers above are not declared in this repository's two
        # Android.bp files. They require qualified external Soong modules.
        self.assertEqual(
            sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("Android.bp")),
            ["Android.bp", "rmnetctl/Android.bp"],
        )

    def test_legacy_rmnet_data_kernel_uapi_is_conditional_only(self):
        c = read("rmnetctl/src/librmnetctl.c")
        self.assertIn(
            "#ifdef USE_OLD_RMNET_DATA\n#include <linux/rmnet_data.h>\n#endif", c
        )
        self.assertIn("#include <linux/rtnetlink.h>", c)
        self.assertIn("#include <linux/netlink.h>", c)
        self.assertIn("RTM_NEWLINK", c)
        self.assertIn("IFLA_LINK", c)
        self.assertIn("NLM_F_REQUEST | NLM_F_ACK", c)
        self.assertIn("struct rtattr", c)
        # Modern rtnetlink path is real, but it still needs the correct
        # Qualcomm kernel RMNET implementation and vendor/userspace ABI.

    def test_public_api_diverges_by_legacy_flag(self):
        header = read("rmnetctl/inc/librmnetctl.h")
        self.assertIn("#ifdef USE_OLD_RMNET_DATA", header)
        self.assertIn("int rmnetctl_init(", header)
        self.assertIn("int rtrmnet_set_qmi_scale(", header)
        self.assertIn("const char *rtrmnet_ll_status_to_text(", header)
        self.assertIn("RMNETCTL_API_ERR_RTA_FAILURE", header)
        self.assertIn("#define RMNETCTL_INVALID_ARG 3", header)

    def test_historical_product_package_only_selects_rmnet_library(self):
        mk = read("dataservices_vendor_product.mk")
        self.assertIn("DATA_OSS := librmnetctl", mk)
        self.assertIn("PRODUCT_PACKAGES += $(DATA_OSS)", mk)
        self.assertNotIn("rmnetcli", mk)
        self.assertNotIn("datatop", mk)
        # Do not import old product makefiles into default AOSP17 platform.

    def test_datatop_is_legacy_make_diagnostic_not_required_aosp_hal(self):
        outer = read("datatop/Android.mk")
        mk = read("datatop/src/Android.mk")
        c = read("datatop/src/datatop.c")
        self.assertIn("project-path-for,qcom-dataservices", outer)
        self.assertIn("LOCAL_MODULE := datatop", mk)
        self.assertIn("LOCAL_MODULE_TAGS := optional", mk)
        self.assertIn("LOCAL_CLANG := true", mk)
        self.assertIn('/sys/module/rmnet_shs/parameters/', c)
        self.assertIn('/sys/module/rmnet_data/parameters/', c)
        self.assertIn('/sys/class/net/rmnet_ipa0/statistics/', c)
        # These sysfs/debug counters are not universal AOSP17 interfaces.

    def test_automake_host_build_is_separate_from_aosp_soong(self):
        auto = read("configure.ac")
        self.assertIn("AC_INIT([data-oss], [1.0.0])", auto)
        self.assertIn("AC_ARG_WITH(sanitized-headers", auto)
        self.assertIn("AC_CHECK_HEADERS(", auto)
        self.assertIn("linux/rmnet_data.h", auto)
        self.assertIn("PKG_CHECK_MODULES(GLIB", auto)
        root = read("Makefile.am")
        self.assertIn("SUBDIRS = rmnetctl/src rmnetctl/cli", root)
        self.assertNotIn("datatop", root)

    def test_public_header_defines_error_text_storage_not_extern_only(self):
        h = read("rmnetctl/inc/librmnetctl.h")
        self.assertIn("char rmnetctl_error_code_text", h)
        self.assertIn("[RMNETCTL_API_ERR_ENUM_LENGTH][RMNETCTL_ERR_MSG_SIZE]", h)
        self.assertNotIn("extern char rmnetctl_error_code_text", h)
        # Static risk: including this public header in multiple object files
        # of ONE library can introduce duplicate global definitions.
        # Not demonstrated by linking the actual Android17 target.

    def test_official_aosp17_networking_and_build_sources_stay_selected(self):
        root = ET.fromstring(pin("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        paths = {node.get("path"): node.get("name")
                 for node in root.iter("project")}
        for path, name in (
            ("build/soong", "platform/build/soong"),
            ("system/netd", "platform/system/netd"),
            ("system/bpf", "platform/system/bpf"),
            ("packages/modules/Connectivity", "platform/packages/modules/Connectivity"),
            ("system/core", "platform/system/core"),
        ):
            with self.subTest(path=path):
                self.assertEqual(paths[path], name)
        self.assertNotIn(LEGACY_PATH, paths)
        self.assertNotIn(LEGACY_NAME, paths.values())

    def test_platform_default_does_not_import_old_rmnet(self):
        root = ET.fromstring(pin("PE_AOSP17_DEFAULT"))
        self.assertEqual(
            [node.get("name") for node in root.findall("include")],
            ["aosp17_pe_p2_kernel_configs.xml"],
        )
        self.assertFalse(any(node.get("path") == LEGACY_PATH or
                             node.get("name") == LEGACY_NAME
                             for node in root.iter("project")))

if __name__ == "__main__":
    unittest.main(verbosity=2)
