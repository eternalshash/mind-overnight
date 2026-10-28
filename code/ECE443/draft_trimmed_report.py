import re

text_sections = {}

# 1. Header Metadata
doc_title = "ECE 443 / 518: Introduction to Computer Cyber Security"
doc_subtitle = "Project 3: Security in the Wild\nTechnical Analysis of the Anker Eufy Security Camera Vulnerabilities"

# Section 1
s1_title = "1. Threat Model and Security Policy"
s1_text = """Home security cameras operate inside intimate residential spaces, capturing real time video, recorded clips, and audio from bedrooms, hallways, and living areas. Beyond raw video streams, modern smart cameras process high resolution facial crops, biometric feature vectors, user authentication tokens, and hardware identifiers like serial numbers and MAC addresses. Because this telemetry directly reflects the daily routines and personal privacy of occupants, protecting these assets is a critical engineering requirement.

A sound security policy for residential surveillance requires five core properties:
1. Confidentiality: Live and stored footage must be accessible exclusively to authenticated account holders.
2. Integrity: Video streams, control commands, and metadata must resist in-transit tampering or injection.
3. User Sovereignty and Informed Consent: No visual data or facial crops may leave local on-premises hardware without explicit user permission.
4. Cryptographic Rigor: Dynamic, per-session encryption keys must protect all transmissions, with private keys anchored in local hardware security modules.
5. Verifiable Erasure: Deletion requests from the user must trigger irreversible removal across all physical and cloud storage tiers.

The threat model must account for three distinct adversaries:
First, external remote attackers on the public Internet who target exposed web services and media streaming ports.
Second, local network eavesdroppers who intercept unencrypted wireless packets over Wi-Fi or transit networks.
Third, cloud insider threats, including company personnel or attackers who breach centralized cloud servers.

Eufy centered its marketing on absolute privacy, promising that video footage stayed strictly local and never reached external servers without permission. Users trusted that the cameras guarding their homes would not become surveillance backdoors. The actual technical implementation contradicted every one of these promises."""

# Section 2
s2_title = "2. Technical Breakdown of Security Flaws"
s2_text = """The fundamental flaw in Eufy's system was architectural misrepresentation. While advertising zero cloud dependencies and on-device storage, the cameras actively uploaded facial recognition crops, full thumbnails, and account metadata to Amazon Web Services servers whenever motion was detected. These uploads occurred even when users disabled cloud features and opted out of cloud processing. Furthermore, facial recognition data persisted on AWS infrastructure after users deleted recordings, and facial profiles were tracked across distinct user accounts without disclosure.

The most critical vulnerability was completely unencrypted video streaming accessible through open cloud endpoints. Independent researchers discovered that anyone could stream live video from customer cameras using standard media software like VLC Player. The exploit chain operated through four distinct steps:
1. An attacker or user authenticated to the Eufy web portal.
2. By enabling browser developer tools, the client exposed internal API calls requesting cloud relay streams.
3. The server returned a plaintext streaming URL linking to Eufy's cloud media servers.
4. This URL could be copied directly into VLC Player, initiating an unencrypted live video feed without requiring further credentials.

The structure of the streaming URL was fundamentally insecure. It contained the camera serial number encoded in standard Base64, an epoch timestamp, an MD5 token, and a static hexadecimal signature. Because Base64 is fully reversible, anyone with access to the serial number could derive the endpoint. Serial numbers were printed directly on retail boxes and camera bodies, allowing opportunistic attackers to target discarded packaging. Furthermore, the media server never validated timestamp freshness, meaning expired or fabricated timestamps were accepted without rejection.

When Eufy did apply encryption, the implementation failed standard cryptographic rules. Researchers decompiled the camera firmware and extracted a shared, hardcoded symmetric key: 'ZXSecurity17Cam@'. Every camera across the product line used this identical 16-byte key for AES-128 encryption. The cipher ran in Electronic Codebook mode without dynamic initialization vectors, producing identical ciphertext blocks for identical plaintext inputs. This static key had been visible in public configuration files since 2019, exposing thousands of households for years.

Finally, Eufy failed basic data governance standards. Deleting video clips from the mobile application left thumbnail images and facial crops intact on AWS S3 buckets. Users could access cloud-stored images even after powering off the local base station, and data remained reachable following complete account deletion. This violated core privacy principles and contravened European Union GDPR mandates regarding the right to erasure."""

# Section 3
s3_title = "3. Evaluation of Remediation, Emerging Threats, and Improvements"
s3_text = """Anker's initial response worsened the security breach. When security researchers presented verifiable proof of unencrypted streaming, the company publicly denied that VLC playback was possible. Only after major technology publications replicated the exploit across multiple states did Anker acknowledge the flaws and begin issuing patches.

Eufy rolled out several technical fixes to resolve the disclosed vulnerabilities:
1. Debug mode and verbose API logging were stripped from the production web portal.
2. Plaintext streaming links were disabled, and video delivery was migrated to WebRTC with mandatory Datagram Transport Layer Security and Secure Real-time Transport Protocol encryption.
3. The hardcoded key 'ZXSecurity17Cam@' was retired in favor of dynamic session key exchanges.
4. Mobile applications were updated to inform users that push notification thumbnails require cloud transit unless text-only mode is selected.

While these measures closed the trivial VLC streaming exploit, several significant threats remain. WebRTC relies on central signaling servers to exchange session descriptions. An adversary observing signaling metadata can map network addresses, monitor connection intervals, and infer when occupants are home. Additionally, because Eufy manages the signaling servers, users remain vulnerable to cloud insider attacks or server compromises where unauthorized public keys could be injected. The system also remains dependent on closed, proprietary firmware updates that cannot be audited by the user.

To build a genuinely secure camera system, several technical improvements are required:
First, implement client-side zero-knowledge encryption where video feeds are encrypted using public keys held exclusively on the user's mobile device, preventing cloud servers from viewing raw video.
Second, generate distinct cryptographic keys on-device using a hardware security module, eliminating shared firmware secrets.
Third, enforce mutual TLS authentication and certificate pinning between the camera and authorized clients to block proxy interception.
Fourth, establish true local network independence, allowing users to stream video directly over a local area network through authenticated local RTSP without external cloud dependencies.
Fifth, maintain an active third-party audit schedule and a public bug bounty program to identify and remediate vulnerabilities before commercial release."""

# Section 4
s4_title = "4. Conclusion"
s4_text = """The Eufy security camera incident illustrates the severe risks created when marketing claims diverge from engineering reality. Eufy promised private, on-device storage while secretly routing unencrypted video, facial crops, and biometric data through cloud servers. The failure combined broken access controls, trivial hardcoded cryptography, and irresponsible data retention policies. While emergency patches fixed the immediate streaming loophole, the incident damaged customer trust and demonstrated that proprietary IoT systems require constant external scrutiny. Authentic consumer security requires transparent system architecture, independent audits, and cryptographic enforcement rather than unverified corporate promises."""

# Verification
all_text = f"{doc_title} {doc_subtitle} {s1_text} {s2_text} {s3_text} {s4_text}"

words = len(all_text.split())
print(f"Total word count: {words}")

# Check em/en dashes
dashes = re.findall(r'[—–]', all_text)
print(f"Dashes found: {len(dashes)}")
assert len(dashes) == 0, f"Error: found dashes: {dashes}"

# Check banned words
banned = [w for w in ['delve', 'utilize', 'tapestry', 'moreover', 'ultimately'] if w in all_text.lower()]
print(f"Banned words found: {banned}")
assert len(banned) == 0, f"Error: found banned words: {banned}"

