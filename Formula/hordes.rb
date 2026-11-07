class Hordes < Formula
  desc "Infernal Hordes decision engine"
  homepage "https://github.com/rbuck/hordes-rs"
  license "MIT"

  if OS.mac? && Hardware::CPU.arm?
    url "https://api.github.com/repos/rbuck/hordes-rs/releases/assets/720903905",
        headers: [
          "Accept: application/octet-stream",
          "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
          "X-GitHub-Api-Version: 2022-11-28",
        ]
    sha256 "c2476ad9fa0b1ebcc3d7585dc0ff0aa79ab609d50c7c9fbba6a6056baa217604"
  end

  if OS.mac? && Hardware::CPU.intel?
    url "https://api.github.com/repos/rbuck/hordes-rs/releases/assets/720903908",
        headers: [
          "Accept: application/octet-stream",
          "Authorization: Bearer #{ENV.fetch("HOMEBREW_GITHUB_API_TOKEN")}",
          "X-GitHub-Api-Version: 2022-11-28",
        ]
    sha256 "9aa22a97f67e70e23fae343f0c87f9fbeb58febbbecb81d6b7f4ae04e7bbdc33"
  end

  if OS.linux? && Hardware::CPU.intel?
    url "https://github.com/rbuck/hordes-rs/releases/download/v0.7.3/hordes-0.7.3-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "4b99de0e0af56aeb4591310b183ebbb80e17b107153c72925946ebb9aaf37565"
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
