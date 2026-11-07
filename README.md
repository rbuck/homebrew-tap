# Robert Buck Organizational Homebrew Tap

This is the shared Homebrew tap for the rbuck organization. It hosts formulae for various command-line tools so they can be installed and updated with brew.

## How do I install these formulae?

```shell
brew tap rbuck/tap
brew trust rbuck/tap
brew install rbuck/tap/<formula>
```

After the tap is added you can also install by short name, e.g. brew install <forumla> .

## Contributing

To build, install, and test:

To build, install, and test:

```shell
brew style rbuck/tap/<formula>
brew audit --new --formula rbuck/tap/<formula>
brew install --build-from-source rbuck/tap/<formula>
brew test rbuck/tap/<formula>
brew test --verbose rbuck/tap/hordes
```

To update a formula from a GitHub release:

```shell
python scripts/update_formula.py hordes v0.7.3
```

The script reads the repository from the formula's `homepage`, infers release
asset names from the existing platform URLs, and updates their URLs and SHA256
values from the release's `SHA256SUMS.txt`. Authenticate with `gh auth login`
before running it.

Prefix all the above commands with the following for private repositories:

```shell
HOMEBREW_GITHUB_API_TOKEN=$(gh auth token)
```

## Documentation

`brew help`, `man brew` or check [Homebrew's documentation](https://docs.brew.sh).
