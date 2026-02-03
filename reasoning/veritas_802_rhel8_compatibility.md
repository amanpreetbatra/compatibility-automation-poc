# Veritas InfoScale 8.0.2 Compatibility Envelope for RHEL 8 Kernels

## Supported Kernel Envelope (Min/Max)
Veritas InfoScale 8.0.2 is documented as certified on RHEL 8.2 through RHEL 8.7 GA streams, covering kernel builds **4.18.0-193.el8** (min) through **4.18.0-425.el8** (max). These bounds reflect the versions listed in the Veritas InfoScale 8.0.2 Product Compatibility List (October 2023 update) tied to corresponding Red Hat errata.

## Out-of-Envelope Kernels
Kernel builds below 4.18.0-193.el8 or above 4.18.0-425.el8 are not listed as supported. Examples include **4.18.0-80.el8** (pre-envelope) and **4.18.0-477.el8**, **4.18.0-513.el8** (post-envelope). These require explicit vendor confirmation prior to rollout.

## Operational Risk of Exceeding the Envelope
Running InfoScale 8.0.2 outside the documented kernel envelope can lead to storage stack instability, kernel module load failures, or degraded clustering behavior. These conditions raise the likelihood of unplanned failovers or data path interruptions in production environments.

## References
- Veritas InfoScale 8.0.2 Product Compatibility List (October 2023) — vendor_hcl
- Veritas InfoScale 8.0.2 Release Notes — release_notes
- Red Hat Errata Advisory stream for RHEL 8.7 GA kernel 4.18.0-425.el8 — advisory
