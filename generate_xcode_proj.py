import os

def create_xcode_project():
    proj_dir = "/Users/emil/Documents/Codex/SplatCat/apps/mobile/SplatCatCompanion/SplatCatCompanion.xcodeproj"
    os.makedirs(proj_dir, exist_ok=True)
    
    pbxproj_content = """// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 56;
	objects = {

/* Begin PBXBuildFile section */
		1001 /* SplatCatCompanionApp.swift in Sources */ = {isa = PBXBuildFile; fileRef = 2001 /* SplatCatCompanionApp.swift */; };
		1002 /* ViewController.swift in Sources */ = {isa = PBXBuildFile; fileRef = 2002 /* ViewController.swift */; };
		1003 /* HeatmapShader.metal in Sources */ = {isa = PBXBuildFile; fileRef = 2003 /* HeatmapShader.metal */; };
		1004 /* StreamerService.swift in Sources */ = {isa = PBXBuildFile; fileRef = 2004 /* StreamerService.swift */; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		0001 /* SplatCatCompanion.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = SplatCatCompanion.app; sourceTree = BUILT_PRODUCTS_DIR; };
		2001 /* SplatCatCompanionApp.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = SplatCatCompanionApp.swift; sourceTree = "<group>"; };
		2002 /* ViewController.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ViewController.swift; sourceTree = "<group>"; };
		2003 /* HeatmapShader.metal */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.metal; path = HeatmapShader.metal; sourceTree = "<group>"; };
		2004 /* StreamerService.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = StreamerService.swift; sourceTree = "<group>"; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		3001 /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		4001 /* Main Group */ = {
			isa = PBXGroup;
			children = (
				2001 /* SplatCatCompanionApp.swift */,
				2002 /* ViewController.swift */,
				2003 /* HeatmapShader.metal */,
				2004 /* StreamerService.swift */,
				0001 /* SplatCatCompanion.app */,
			);
			sourceTree = "<group>";
		};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		5001 /* SplatCatCompanion */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = 6001 /* Build configuration list for PBXNativeTarget "SplatCatCompanion" */;
			buildPhases = (
				7001 /* Sources */,
				3001 /* Frameworks */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = SplatCatCompanion;
			productName = SplatCatCompanion;
			productReference = 0001 /* SplatCatCompanion.app */;
			productType = "com.apple.product-type.application";
		};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		8001 /* Project object */ = {
			isa = PBXProject;
			attributes = {
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1420;
				LastUpgradeCheck = 1420;
				TargetAttributes = {
					5001 = {
						CreatedOnToolsVersion = 14.2;
					};
				};
			};
			buildConfigurationList = 6002 /* Build configuration list for PBXProject "SplatCatCompanion" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = 4001 /* Main Group */;
			productRefGroup = 4001;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				5001 /* SplatCatCompanion */,
			);
		};
/* End PBXProject section */

/* Begin PBXSourcesBuildPhase section */
		7001 /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				1001 /* SplatCatCompanionApp.swift in Sources */,
				1002 /* ViewController.swift in Sources */,
				1003 /* HeatmapShader.metal in Sources */,
				1004 /* StreamerService.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		9001 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_KEY_NSCameraUsageDescription = "SplatCat requires camera access for 3D scanning";
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.splatcat.companion;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SDKROOT = iphoneos;
				SWIFT_EMIT_LOC_TARGETS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Debug;
		};
		9002 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_KEY_NSCameraUsageDescription = "SplatCat requires camera access for 3D scanning";
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.splatcat.companion;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SDKROOT = iphoneos;
				SWIFT_EMIT_LOC_TARGETS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Release;
		};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		6001 /* Build configuration list for PBXNativeTarget "SplatCatCompanion" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				9001 /* Debug */,
				9002 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		6002 /* Build configuration list for PBXProject "SplatCatCompanion" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				9001 /* Debug */,
				9002 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
/* End XCConfigurationList section */
	};
	rootObject = 8001 /* Project object */;
}
"""
    with open(os.path.join(proj_dir, "project.pbxproj"), "w") as f:
        f.write(pbxproj_content)
    print(f"Successfully generated {proj_dir}")

if __name__ == "__main__":
    create_xcode_project()
