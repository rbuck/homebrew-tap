class Hordes < Formula
  desc "Infernal Hordes decision engine"
  homepage "https://github.com/rbuck/hordes-rs"
  license "MIT"

  if OS.mac? && Hardware::CPU.arm?
    url "https://api.github.com/repos/rbuck/hordes-rs/releases/assets/720773340",
        headers: [
          "Accept: application/octet-stream",
          "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
          "X-GitHub-Api-Version: 2022-11-28",
        ]
    sha256 "594a2e4b9f3d60d226d6b73460251f83f6fd78a223b5758fc2fe74a314f75159"
  end

  if OS.mac? && Hardware::CPU.intel?
    url "https://api.github.com/repos/rbuck/hordes-rs/releases/assets/720773333",
        headers: [
          "Accept: application/octet-stream",
          "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
          "X-GitHub-Api-Version: 2022-11-28",
        ]
    sha256 "1765bc9df6f7b1f86d7640982a210100ed7f100f2708c4ccbb2dde65934953e0"
  end

  if OS.linux? && Hardware::CPU.intel?
    url "https://github.com/rbuck/hordes-rs/releases/download/v0.7.0/hordes-rs-0.7.0-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "d2dffe1d99544ee43481cbde0bb3aa23f4757c589fbb3b21717f0619cfaccd4d"
  end

  def install
    bin.install "bin/hordes-cli"
    bin.install "bin/hordes-tui"
    (prefix/"data").install "data/rules.toml"
    doc.install "README.md", "LICENSE"
  end

  test do
    assert_match "hordes-cli", shell_output("#{bin}/hordes-cli --help")
    assert_match "hordes-tui", shell_output("#{bin}/hordes-tui --help")
    assert_path_exists prefix/"data/rules.toml"
  end
end
