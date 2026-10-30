UBports' Halium patches from the `android13-5.15-halium` branch of
https://gitlab.com/ubports/porting/community-ports/android12/generic/kernel-android-common
(commits 0e6b4763..260c66c2), exported with `git format-patch`.

They keep the GKI module ABI (SYSVIPC state lives past the end of task_struct
instead of inside it), so applied to Motorola's 5.15.185 tree the stock vendor
modules still load. UBports' own branch is 5.15.178, whose symbol CRCs don't
match the phone's 5.15.185 modules.
