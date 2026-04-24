-- Python-only extension; premake returns the source directory.
local ext = get_current_extension_info()
project_ext(ext)
repo_build.prebuild_link {
    { "mitlab", ext.target_dir.."/mitlab" },
    { "config", ext.target_dir.."/config" },
}
