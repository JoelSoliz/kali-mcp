"""Curated catalog of common Kali Linux pentesting tools."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CatalogEntry:
    binary: str
    category: str
    man_page: str | None = None
    description: str = ""
    version_flags: list[str] = field(default_factory=lambda: ["--version", "-V", "-v"])
    packages: list[str] = field(default_factory=list)


# Curated list used for reliable discovery on Kali. Extend as needed.
KALI_TOOL_CATALOG: list[CatalogEntry] = [
    CatalogEntry("nmap", "reconnaissance", description="Network mapper and port scanner"),
    CatalogEntry("masscan", "reconnaissance", description="Fast port scanner"),
    CatalogEntry("rustscan", "reconnaissance", description="Modern fast port scanner"),
    CatalogEntry("whatweb", "reconnaissance", description="Web technology fingerprinting"),
    CatalogEntry("sslscan", "reconnaissance", description="SSL/TLS service enumeration"),
    CatalogEntry("dig", "reconnaissance", description="DNS lookup utility"),
    CatalogEntry("host", "reconnaissance", description="DNS lookup utility"),
    CatalogEntry("whois", "reconnaissance", description="WHOIS client"),
    CatalogEntry("theharvester", "reconnaissance", description="OSINT email and subdomain harvester"),
    CatalogEntry("recon-ng", "reconnaissance", description="Web reconnaissance framework"),
    CatalogEntry("nikto", "web", description="Web server vulnerability scanner"),
    CatalogEntry("wpscan", "web", description="WordPress vulnerability scanner", version_flags=["--version"]),
    CatalogEntry("gobuster", "web", description="Directory and DNS brute-forcer"),
    CatalogEntry("dirb", "web", description="Web content scanner"),
    CatalogEntry("ffuf", "web", description="Fast web fuzzer"),
    CatalogEntry("wfuzz", "web", description="Web application fuzzer"),
    CatalogEntry("sqlmap", "web", description="Automatic SQL injection tool"),
    CatalogEntry("commix", "web", description="Command injection exploitation tool"),
    CatalogEntry("curl", "web", description="HTTP client for probing endpoints"),
    CatalogEntry("wget", "web", description="HTTP/file retrieval client"),
    CatalogEntry("zaproxy", "web", description="OWASP ZAP proxy", man_page="zaproxy"),
    CatalogEntry("zap.sh", "web", description="OWASP ZAP launcher", man_page="zaproxy"),
    CatalogEntry("hydra", "exploitation", description="Network logon cracker"),
    CatalogEntry("medusa", "exploitation", description="Parallel login brute-forcer"),
    CatalogEntry("msfconsole", "exploitation", description="Metasploit Framework console"),
    CatalogEntry("searchsploit", "exploitation", description="Exploit-DB local search"),
    CatalogEntry("john", "passwords", description="John the Ripper password cracker", man_page="john"),
    CatalogEntry("hashcat", "passwords", description="Advanced password recovery"),
    CatalogEntry("hash-identifier", "passwords", description="Hash type identifier"),
    CatalogEntry("crunch", "passwords", description="Wordlist generator"),
    CatalogEntry("cewl", "passwords", description="Custom wordlist generator from websites"),
    CatalogEntry("enum4linux", "windows", description="Windows/Samba enumeration tool"),
    CatalogEntry("enum4linux-ng", "windows", description="Next-gen enum4linux"),
    CatalogEntry("smbclient", "windows", description="Samba SMB client"),
    CatalogEntry("rpcclient", "windows", description="MS-RPC client"),
    CatalogEntry("responder", "windows", description="LLMNR/NBT-NS/mDNS poisoner"),
    CatalogEntry("impacket-psexec", "windows", description="Impacket PsExec client"),
    CatalogEntry("impacket-smbclient", "windows", description="Impacket SMB client"),
    CatalogEntry("impacket-secretsdump", "windows", description="Impacket secrets dumper"),
    CatalogEntry("aircrack-ng", "wireless", description="WiFi security auditing suite"),
    CatalogEntry("airodump-ng", "wireless", description="Wireless packet capture"),
    CatalogEntry("reaver", "wireless", description="WPS brute-force attack tool"),
    CatalogEntry("wifite", "wireless", description="Automated wireless auditor"),
    CatalogEntry("tcpdump", "sniffing", description="Network packet analyzer"),
    CatalogEntry("tshark", "sniffing", description="Wireshark CLI packet analyzer"),
    CatalogEntry("netcat", "utility", description="Network swiss army knife", man_page="nc"),
    CatalogEntry("nc", "utility", description="Netcat network utility"),
    CatalogEntry("socat", "utility", description="Multipurpose relay tool"),
    CatalogEntry("proxychains4", "utility", description="Proxy chains tool", man_page="proxychains"),
    CatalogEntry("binwalk", "forensics", description="Firmware analysis tool"),
    CatalogEntry("foremost", "forensics", description="File carving tool"),
    CatalogEntry("steghide", "forensics", description="Steganography tool"),
    CatalogEntry("exiftool", "forensics", description="Metadata reader/writer"),
]

CATEGORY_KEYWORDS = {
    "reconnaissance": ("scan", "recon", "dns", "network", "discover", "enumerate"),
    "web": ("http", "web", "url", "cgi", "wordpress", "directory"),
    "exploitation": ("exploit", "inject", "payload", "shell"),
    "passwords": ("password", "hash", "crack", "wordlist"),
    "windows": ("smb", "samba", "windows", "ldap", "rpc"),
    "wireless": ("wifi", "wireless", "802.11", "wpa"),
    "sniffing": ("packet", "capture", "sniff", "pcap"),
    "forensics": ("forensic", "carve", "stego", "metadata"),
    "utility": ("utility", "tool", "relay", "proxy"),
}

# Well-known parameter layouts override generic man-derived defaults.
TOOL_PARAMETER_TEMPLATES: dict[str, list[dict]] = {
    "nmap": [
        {
            "name": "target",
            "description": "IP address, hostname, or CIDR range to scan",
            "type": "string",
            "required": True,
            "argStyle": "positional",
            "position": 99,
        },
        {
            "name": "scan_type",
            "description": "Scan type flags (e.g. -sV, -sC, -sS)",
            "type": "string",
            "default": "-sV",
            "argStyle": "append",
        },
        {
            "name": "ports",
            "description": "Ports or ranges (passed as -p value)",
            "type": "string",
            "default": "",
            "flag": "-p",
            "argStyle": "kv",
        },
    ],
    "nikto": [
        {
            "name": "target",
            "description": "Target host or URL",
            "type": "string",
            "required": True,
            "flag": "-h",
            "argStyle": "kv",
        }
    ],
    "wpscan": [
        {
            "name": "url",
            "description": "Target WordPress URL",
            "type": "string",
            "required": True,
            "flag": "--url",
            "argStyle": "kv",
        }
    ],
    "gobuster": [
        {
            "name": "mode",
            "description": "Gobuster mode: dir, dns, fuzz, or vhost",
            "type": "string",
            "default": "dir",
            "argStyle": "positional",
            "position": 0,
        },
        {
            "name": "url",
            "description": "Target URL",
            "type": "string",
            "required": True,
            "flag": "-u",
            "argStyle": "kv",
        },
        {
            "name": "wordlist",
            "description": "Wordlist path",
            "type": "string",
            "default": "/usr/share/wordlists/dirb/common.txt",
            "flag": "-w",
            "argStyle": "kv",
        },
    ],
    "sqlmap": [
        {
            "name": "url",
            "description": "Target URL",
            "type": "string",
            "required": True,
            "flag": "-u",
            "argStyle": "kv",
        }
    ],
    "curl": [
        {
            "name": "url",
            "description": "Target URL",
            "type": "string",
            "required": True,
            "argStyle": "positional",
            "position": 0,
        },
        {
            "name": "include_headers",
            "description": "Include response headers in output",
            "type": "boolean",
            "default": True,
            "flag": "-i",
            "argStyle": "flag",
        },
    ],
    "hydra": [
        {
            "name": "target",
            "description": "Target IP or hostname",
            "type": "string",
            "required": True,
            "argStyle": "positional",
            "position": 0,
        },
        {
            "name": "service",
            "description": "Service to attack (ssh, ftp, http-post-form, etc.)",
            "type": "string",
            "required": True,
            "argStyle": "positional",
            "position": 1,
        },
    ],
}

TOOL_FIXED_ARGS: dict[str, list[str]] = {
    "wpscan": ["--no-update"],
    "nmap": ["-T4", "-Pn"],
    "curl": ["-sS", "-L", "--max-time", "30"],
    "whatweb": ["-a", "3"],
}

# Flags commonly used as primary targets in man pages.
TARGET_FLAG_HINTS = ("-h", "-u", "--url", "--target", "-t", "--host", "-H", "-p")
