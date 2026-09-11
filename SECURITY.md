# Security Policy

## Supported versions

WitDL is pre-1.0. Security fixes are applied to the latest release on the
`main` branch.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a vulnerability

Please **do not** report security vulnerabilities through public GitHub issues,
discussions, or pull requests.

Instead, report them privately to marouane.amanar07@gmail.com. If you prefer, you can use
GitHub's [private vulnerability reporting][gh-pvr] on the repository's
**Security** tab.

Please include:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept if possible)
- Affected version(s) and platform
- Any suggested mitigation

We aim to acknowledge reports within a few days and will keep you updated on the
fix and disclosure timeline.

## Scope and threat model

WitDL downloads media from third-party hosts and processes obfuscated data
embedded in web pages. Relevant concerns include:

- Malicious or tampered download URLs returned by a hoster
- Decompression of untrusted archives (hoster-supplied ZIP wrappers)
- Command injection through values passed to `wget`/`curl`

Reports about vulnerabilities in the upstream WitAnime site or third-party
hosters are out of scope; please contact those operators directly.

## Legal notice

WitDL is a tool. You are responsible for how you use it and for complying with
the laws, terms of service, and copyright rules that apply to you. Do not use it
to download content you do not have the right to access.

[gh-pvr]: https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability
