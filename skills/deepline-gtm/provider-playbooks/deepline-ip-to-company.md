# Deepline IP to Company — Agent Guidance

Use this managed integration when a workflow has a public IP address and needs
company identification or firmographic data. Deepline manages the upstream
credential, so workspaces cannot connect or override this provider.

Use `deepline_ip_to_company_find_company_by_ip` with a public IPv4 address.
Do not submit private, loopback, or reserved addresses.
