class Hordes < Formula
  desc "Infernal Hordes decision engine"
  homepage "https://github.com/rbuck/hordes-rs"
  license "MIT"

  if OS.mac? && Hardware::CPU.arm?
    url "https://api.github.com/repos/rbuck/hordes-rs/releases/assets/721708973",
        headers: [
          "Accept: application/octet-stream",
          "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
          "X-GitHub-Api-Version: 2022-11-28",
        ]
    sha256 "dca61ee6ff9850d024ab8a51036860a2800dd6a4151ed8b27768a744987c5ecc"
  end

  if OS.mac? && Hardware::CPU.intel?
    url "https://api.github.com/repos/rbuck/hordes-rs/releases/assets/721708970",
        headers: [
          "Accept: application/octet-stream",
          "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
          "X-GitHub-Api-Version: 2022-11-28",
        ]
    sha256 "6f83385b97abbb8e1a7f06cc28696b62863468ef5dac7ad89de7b2419c0ef1a6"
  end

  if OS.linux? && Hardware::CPU.intel?
    url "https://github.com/rbuck/hordes-rs/releases/download/v0.8.0/hordes-0.8.0-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "14d3aa0b66a84cd4e3237a88b278fe22b172b729663936c3e4f7c9c334615c5a"
  end

  def install
    bin.install "bin/hordes-cli"
    bin.install "bin/hordes-tui"
    (prefix/"data").install "data/rules.toml"
    (prefix/"optimizer-plans").install "optimizer-plans/restore-rules.toml"
    doc.install "README.md", "LICENSE"
  end

  test do
    assert_match "hordes-cli", shell_output("#{bin}/hordes-cli --help")
    assert_match "hordes-tui", shell_output("#{bin}/hordes-tui --help")
    assert_path_exists prefix/"data/rules.toml"
    assert_path_exists prefix/"optimizer-plans/restore-rules.toml"
  end
end
