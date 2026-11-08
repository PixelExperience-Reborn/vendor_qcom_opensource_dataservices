# Stage 197 — Qualcomm Data Services RMNET, kernel UAPI and AOSP 17

**Date:** 2026-11-08. **Current work:** qualify historical PixelExperience repositories against independently pinned, clean Google AOSP android-17.0.0_r1. Finish the audit and then verify a real platform source graph and build. No device trees, SM8475-specific integration or optional features in this stage.

## Qualcomm source provenance

- Repository: https://github.com/PixelExperience-Reborn/vendor_qcom_opensource_dataservices
- Historical seventeen HEAD dfc2ec0112353afdb6db99db8bae7328b42e44f6, dated 2023-07-27. Original tree c2f2692c171be369f0b90248ec457dc50e6ea290; rmnetctl subtree 7de98a2eddfbad2ad2e4268442678769bab61b70 and datatop subtree f43813b9d332bd21d19387ecf30fd5c31d9d8dd7. All original source objects remain untouched.
- The final historical commit conditionally restored the old RMNET_DATA driver support for platforms preceding Kalama. This is Qualcomm engineering history, not evidence that an older kernel interface is selected for PE-Reborn.
- The archived repository has 43 Git source blobs. This is a Qualcomm vendor RMNET control library, a CLI and an old system/network diagnostic called datatop. It is **not** a full modem stack, RIL, telephony framework, QMI daemon, kernel RMNET driver or Android networking module.

## Actual technical interface dependencies

1. **Two intentionally distinct RMNET paths.** The Soong file rmnetctl/Android.bp defines a bool variable old_rmnet_data in the rmnetctl namespace. Only when selected does it emit -DUSE_OLD_RMNET_DATA. In rmnetctl/src/librmnetctl.c, linux/rmnet_data.h is included only under that conditional. The other path uses Linux rtnetlink and NETLINK_ROUTE APIs, including RTM_NEWLINK and route link attributes. The archive already differentiates legacy RMNET from newer-in-archive APIs; neither can be declared compatible with any specific Android17 kernel without testing.
2. **Soong dependencies not closed in this checkout.** librmnetctl requires the external qti_kernel_headers and device_kernel_headers modules. Their providers and matching effective kernel UAPI are not defined by this archive. Do not invent them or import LineageOS device trees to satisfy Soong.
3. **Only verified product inclusion.** dataservices_vendor_product.mk adds librmnetctl to PRODUCT_PACKAGES. The rmnetcli binary is separately declared in Soong but is not requested by this product snippet. The AOSP17 default.xml does not import this source.
4. **Datatop is not an Android17 platform HAL.** datatop/src/Android.mk is an old optional Android.mk diagnostic that reads /sys/module/rmnet* and /sys/class/net/rmnet_ipa0. Its paths are tied to old Qualcomm kernel interfaces, and it is not selected in the data-services product snippet.
5. **Autotools is not Android17 Soong.** configure.ac/Makefile.am provide a separate GNU Autotools GLib build that checks linux/rmnet_data.h and accepts sanitized Linux headers; successful Autotools syntax would not qualify Android17 source/ABI compatibility.
6. **Public-header portability concern.** rmnetctl/inc/librmnetctl.h defines storage for the global rmnetctl_error_code_text array in the header instead of making an extern-only declaration; multiple inclusion by different objects in a single link unit could cause duplicate definitions. It relies on fixed-width integer definitions provided by its include context. Host smoke compilation of one translation unit does not establish target linking.

## AOSP17 ownership and Qualcomm priority

AOSP17 official projects remain the owners of build/soong, system/netd, system/bpf, packages/modules/Connectivity and system/core. They are not interchangeable with the optional vendor RMNET control API. Qualcomm RMNET is not categorically disabled: a future **validated** modem/vendor consumer may require a compatible library and kernel UAPI. Prioritize up-to-date, pinned Qualcomm source **only** after identifying its real interface consumer and matching kernel implementation. Newer is not equivalent to compatible.

**Decision:** preserve the historical Qualcomm repository, do not import this old 2023 checkout into active/candidate AOSP17 source manifests, and guard its exact path plus known aliases against accidental reintroduction. This is not a ban on separately reviewed modern Qualcomm RMNET components.

## Implemented CI and manifest gates

- Python tests pin original Git history/subtrees, inspect legacy compile flags and rtnetlink interfaces, Soong kernel-header providers, historic datatop and Autotools packaging, Google AOSP17 network ownership and unchanged default manifest.
- A host Clang C test compiles and executes a *single translation unit* including the unmodified public librmnetctl.h, and verifies error enum/table dimensions. It never opens sockets or invokes Qualcomm kernel, modem or vendor binaries. A host-header test is narrower than a real Android17 Soong/ELF build.
- GitHub Actions pins the PE-Reborn manifest commit, runs the complete active/candidate manifest regression suite and checks all 135 historical repository rows.
- Companion Manifest Draft PR #2 adds path/known-alias protection, two negative regression tests and matrix stage197. Original seventeen source and Android17 default.xml unchanged. No LF52406/LineageOS tree, SM8475 integration or optional features are touched.

## After 135/135 historical source audits

Next, independently qualify the *actual* complete Google AOSP17 platform graph: run Google's repo manifest resolver with full include/remove semantics, real repo sync, Soong bootstrap, host build tools, platform target build and image packaging, security/API/VINTF checks. Only then address missing dependencies and, in a separate later phase, SM8475 device bring-up. The audit inventory is not a percentage of ROM readiness.

**Not performed here:** complete repo sync or Soong build, Android17 image, vendor RMNET library target build, kernel/firmware ABI tests or physical device boot.
