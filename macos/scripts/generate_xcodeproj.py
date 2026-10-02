"""Regenerates the Xcode project (MVTGUI.xcodeproj) from the files in
macos/MVTGUI/, so adding a Swift file needs no Xcode. Object IDs are hashes of
file paths, so unchanged files keep their IDs.

    python3 macos/scripts/generate_xcodeproj.py                  # after adding or removing files
    python3 macos/scripts/generate_xcodeproj.py --version 4.0.1  # also bumps the build number
"""

import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "MVTGUI"
PBXPROJ = ROOT / "MVTGUI.xcodeproj" / "project.pbxproj"

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument(
    "--version", help="new MARKETING_VERSION, e.g. 4.0.1 (bumps the build number too)"
)
parser.add_argument("--build", type=int, help="new CURRENT_PROJECT_VERSION")
args = parser.parse_args()

current = PBXPROJ.read_text() if PBXPROJ.exists() else ""
version = args.version or re.search(r"MARKETING_VERSION = ([^;]+);", current).group(1)
build = args.build or int(
    re.search(r"CURRENT_PROJECT_VERSION = (\d+);", current).group(1)
) + (1 if args.version else 0)


def oid(name):
    return hashlib.md5(name.encode()).hexdigest()[:24].upper()


# The app folder's own Swift files and asset catalog, then one group per subfolder.
groups = {"": sorted(p.name for p in APP.glob("*.swift")) + ["Assets.xcassets"]}
for folder in sorted(p for p in APP.iterdir() if p.is_dir() and not p.suffix):
    swift = sorted(p.name for p in folder.glob("*.swift"))
    if swift:
        groups[folder.name] = swift

P = {
    k: oid(k)
    for k in [
        "project",
        "rootGroup",
        "appGroup",
        "productsGroup",
        "product",
        "target",
        "sources",
        "frameworks",
        "resources",
        "projCfgList",
        "tgtCfgList",
        "projDebug",
        "projRelease",
        "tgtDebug",
        "tgtRelease",
    ]
}
for g in groups:
    if g:
        P["group:" + g] = oid("group:" + g)

file_refs, build_files, src_phase, res_phase = [], [], [], []
group_children = {g: [] for g in groups}
for g, files in groups.items():
    for f in files:
        path = f"{g}/{f}" if g else f
        ref, bf = oid("ref:" + path), oid("bf:" + path)
        if f.endswith(".swift"):
            ftype = "sourcecode.swift"
            src_phase.append((bf, f))
            phase = "Sources"
        else:
            ftype = "folder.assetcatalog"
            res_phase.append((bf, f))
            phase = "Resources"
        file_refs.append(
            f'\t\t{ref} /* {f} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; path = {f}; sourceTree = "<group>"; }};'
        )
        build_files.append(
            f"\t\t{bf} /* {f} in {phase} */ = {{isa = PBXBuildFile; fileRef = {ref} /* {f} */; }};"
        )
        group_children[g].append((ref, f))

file_refs.append(
    f"\t\t{P['product']} /* MVTGUI.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = MVTGUI.app; sourceTree = BUILT_PRODUCTS_DIR; }};"
)


def children(items):
    return "\n".join(f"\t\t\t\t{i} /* {n} */," for i, n in items)


sub = [(P["group:" + g], g) for g in groups if g]
app_children = sub + group_children[""]
group_sections = [
    f"""\t\t{P["rootGroup"]} = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t\t{P["appGroup"]} /* MVTGUI */,
\t\t\t\t{P["productsGroup"]} /* Products */,
\t\t\t);
\t\t\tsourceTree = "<group>";
\t\t}};""",
    f"""\t\t{P["productsGroup"]} /* Products */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t\t{P["product"]} /* MVTGUI.app */,
\t\t\t);
\t\t\tname = Products;
\t\t\tsourceTree = "<group>";
\t\t}};""",
    f"""\t\t{P["appGroup"]} /* MVTGUI */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{children(app_children)}
\t\t\t);
\t\t\tpath = MVTGUI;
\t\t\tsourceTree = "<group>";
\t\t}};""",
]
for g in groups:
    if not g:
        continue
    group_sections.append(f"""\t\t{P["group:" + g]} /* {g} */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{children(group_children[g])}
\t\t\t);
\t\t\tpath = {g};
\t\t\tsourceTree = "<group>";
\t\t}};""")

common_proj = """\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;
\t\t\t\tCLANG_ENABLE_MODULES = YES;
\t\t\t\tCLANG_ENABLE_OBJC_ARC = YES;
\t\t\t\tCOPY_PHASE_STRIP = NO;
\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;
\t\t\t\tENABLE_USER_SCRIPT_SANDBOXING = YES;
\t\t\t\tGCC_C_LANGUAGE_STANDARD = gnu17;
\t\t\t\tLOCALIZATION_PREFERS_STRING_CATALOGS = YES;
\t\t\t\tMACOSX_DEPLOYMENT_TARGET = 13.0;
\t\t\t\tSDKROOT = macosx;
\t\t\t\tSWIFT_VERSION = 5.0;"""
proj_debug = (
    common_proj
    + """
\t\t\t\tDEBUG_INFORMATION_FORMAT = dwarf;
\t\t\t\tENABLE_TESTABILITY = YES;
\t\t\t\tGCC_OPTIMIZATION_LEVEL = 0;
\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (
\t\t\t\t\t"DEBUG=1",
\t\t\t\t\t"$(inherited)",
\t\t\t\t);
\t\t\t\tONLY_ACTIVE_ARCH = YES;
\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = "DEBUG $(inherited)";
\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";"""
)
proj_release = (
    common_proj
    + """
\t\t\t\tDEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
\t\t\t\tENABLE_NS_ASSERTIONS = NO;
\t\t\t\tSWIFT_COMPILATION_MODE = wholemodule;"""
)
tgt = """\t\t\t\tASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
\t\t\t\tASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
\t\t\t\tCODE_SIGN_IDENTITY = "-";
\t\t\t\tCODE_SIGN_STYLE = Automatic;
\t\t\t\tCOMBINE_HIDPI_IMAGES = YES;
\t\t\t\tCURRENT_PROJECT_VERSION = {build};
\t\t\t\tDEVELOPMENT_TEAM = "";
\t\t\t\tENABLE_APP_SANDBOX = NO;
\t\t\t\tENABLE_HARDENED_RUNTIME = YES;
\t\t\t\tGENERATE_INFOPLIST_FILE = YES;
\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = MVT;
\t\t\t\tINFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.utilities";
\t\t\t\tINFOPLIST_KEY_NSHumanReadableCopyright = "GUI wrapper for the Mobile Verification Toolkit (MVT License 1.1).";
\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (
\t\t\t\t\t"$(inherited)",
\t\t\t\t\t"@executable_path/../Frameworks",
\t\t\t\t);
\t\t\t\tMARKETING_VERSION = {version};
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = io.github.mvtgui.MVTGUI;
\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";
\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;""".replace("{build}", str(build)).replace(
    "{version}", version
)


def cfg(id_, name, body):
    return f"""\t\t{id_} /* {name} */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
{body}
\t\t\t}};
\t\t\tname = {name};
\t\t}};"""


def phase_files(items, phase):
    return "\n".join(f"\t\t\t\t{b} /* {n} in {phase} */," for b, n in items)


out = f"""// !$*UTF8*$!
{{
\tarchiveVersion = 1;
\tclasses = {{
\t}};
\tobjectVersion = 56;
\tobjects = {{

/* Begin PBXBuildFile section */
{chr(10).join(sorted(build_files))}
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
{chr(10).join(sorted(file_refs))}
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
\t\t{P["frameworks"]} /* Frameworks */ = {{
\t\t\tisa = PBXFrameworksBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
{chr(10).join(group_sections)}
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
\t\t{P["target"]} /* MVTGUI */ = {{
\t\t\tisa = PBXNativeTarget;
\t\t\tbuildConfigurationList = {P["tgtCfgList"]} /* Build configuration list for PBXNativeTarget "MVTGUI" */;
\t\t\tbuildPhases = (
\t\t\t\t{P["sources"]} /* Sources */,
\t\t\t\t{P["frameworks"]} /* Frameworks */,
\t\t\t\t{P["resources"]} /* Resources */,
\t\t\t);
\t\t\tbuildRules = (
\t\t\t);
\t\t\tdependencies = (
\t\t\t);
\t\t\tname = MVTGUI;
\t\t\tproductName = MVTGUI;
\t\t\tproductReference = {P["product"]} /* MVTGUI.app */;
\t\t\tproductType = "com.apple.product-type.application";
\t\t}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
\t\t{P["project"]} /* Project object */ = {{
\t\t\tisa = PBXProject;
\t\t\tattributes = {{
\t\t\t\tBuildIndependentTargetsInParallel = 1;
\t\t\t\tLastSwiftUpdateCheck = 1500;
\t\t\t\tLastUpgradeCheck = 1500;
\t\t\t\tTargetAttributes = {{
\t\t\t\t\t{P["target"]} = {{
\t\t\t\t\t\tCreatedOnToolsVersion = 15.0;
\t\t\t\t\t}};
\t\t\t\t}};
\t\t\t}};
\t\t\tbuildConfigurationList = {P["projCfgList"]} /* Build configuration list for PBXProject "MVTGUI" */;
\t\t\tcompatibilityVersion = "Xcode 14.0";
\t\t\tdevelopmentRegion = en;
\t\t\thasScannedForEncodings = 0;
\t\t\tknownRegions = (
\t\t\t\ten,
\t\t\t\tBase,
\t\t\t);
\t\t\tmainGroup = {P["rootGroup"]};
\t\t\tproductRefGroup = {P["productsGroup"]} /* Products */;
\t\t\tprojectDirPath = "";
\t\t\tprojectRoot = "";
\t\t\ttargets = (
\t\t\t\t{P["target"]} /* MVTGUI */,
\t\t\t);
\t\t}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
\t\t{P["resources"]} /* Resources */ = {{
\t\t\tisa = PBXResourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
{phase_files(res_phase, "Resources")}
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
\t\t{P["sources"]} /* Sources */ = {{
\t\t\tisa = PBXSourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
{phase_files(src_phase, "Sources")}
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
{cfg(P["projDebug"], "Debug", proj_debug)}
{cfg(P["projRelease"], "Release", proj_release)}
{cfg(P["tgtDebug"], "Debug", tgt)}
{cfg(P["tgtRelease"], "Release", tgt)}
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
\t\t{P["projCfgList"]} /* Build configuration list for PBXProject "MVTGUI" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{P["projDebug"]} /* Debug */,
\t\t\t\t{P["projRelease"]} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
\t\t{P["tgtCfgList"]} /* Build configuration list for PBXNativeTarget "MVTGUI" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{P["tgtDebug"]} /* Debug */,
\t\t\t\t{P["tgtRelease"]} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
/* End XCConfigurationList section */
\t}};
\trootObject = {P["project"]} /* Project object */;
}}
"""
PBXPROJ.write_text(out)

open(
    ROOT / "MVTGUI.xcodeproj" / "project.xcworkspace/contents.xcworkspacedata", "w"
).write("""<?xml version="1.0" encoding="UTF-8"?>
<Workspace
   version = "1.0">
   <FileRef
      location = "self:">
   </FileRef>
</Workspace>
""")

bref = f'''<BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{P["target"]}"
               BuildableName = "MVTGUI.app"
               BlueprintName = "MVTGUI"
               ReferencedContainer = "container:MVTGUI.xcodeproj">
            </BuildableReference>'''
open(
    ROOT / "MVTGUI.xcodeproj" / "xcshareddata/xcschemes/MVTGUI.xcscheme", "w"
).write(f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1500"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            {bref}
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES"
      shouldAutocreateTestPlan = "YES">
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         {bref}
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         {bref}
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
""")
print(f"MVTGUI.xcodeproj: {len(src_phase)} Swift files, version {version} ({build})")
