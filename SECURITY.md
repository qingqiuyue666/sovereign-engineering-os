# Security

This branch contains V12 foundation leak-prevention gates. They are
contract-only and read-only. They do not call providers, send notifications,
read real secrets, access vault/keyring/KMS, run a daemon, mutate repositories,
or persist raw prompts/provider responses.

Report suspected secret exposure by stopping execution, preserving only
digest-only evidence, and routing the finding through the local audit bundle
surface.
