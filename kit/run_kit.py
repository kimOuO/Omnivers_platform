#!/usr/bin/env python3
import sys
import builtins

# Patch input() BEFORE importing omni.kit_app
_orig_input = builtins.input
def auto_yes_input(prompt=""):
    if "EULA" in prompt or "accept" in prompt.lower():
        print(f"{prompt}Yes (auto-accepted)")
        return "Yes"
    return _orig_input(prompt)

builtins.input = auto_yes_input

# Run omni.kit_app as module
import runpy
runpy.run_module('omni.kit_app', run_name='__main__')
