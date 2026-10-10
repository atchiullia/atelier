# Phase 0 walkthrough: foundation (week 1, about 14 hours)

Goal: put the locks and fences in place before any real code exists. Mistakes about secrets and money are the ones you cannot undo later.

Each step has the same shape, so you can follow it on camera:

- **Say this** is a one-line explanation for the viewer.
- **Do** is what to click or type.
- **You should see** is how you know it worked.
- **If not** covers the problems most likely to appear.

| Step | What | Time |
|---|---|---|
| 0 | Tools, folders, download the files | 0.5 h |
| 1 | Create three repos | 1 h |
| 2 | "Only me" settings | 1 h |
| 3 | Collect the private list | 2 h |
| 4 | Build the guards | 4 h |
| 5 | Decision notes (ADRs) | 2 h |
| 6 | Money alarm in Azure | 2 h |
| 7 | History check, go public, write-up | 2 h |

## Before you press record: what must never be on screen

Anything on this list gives a stranger a map of your house or a key to it. Blur it, cover it or keep it off screen.

- The contents of `leak-patterns/` (open it in an editor only when the camera is off, or show counts only).
- Your `kubectl` context name, node names, internal IPs, your home public IP.
- Any token, at any moment. GitHub shows a new token **once**; copy it with the camera off.
- Azure subscription ID, tenant ID, billing details and your email address.
- Cloudflare account ID, zone IDs, tunnel IDs.

Safe to show: the repo pages, the counts the tool prints, the `LEAK <category> <file>:<line>` lines (they are redacted by design), and public hostnames such as `ebahn.fuhro.network`.

## Step 0: Tools, folders, files (0.5 h)

**Say this:** "I need git, the GitHub CLI, Python, pre-commit and gitleaks. Everything lives under one folder so the three repos sit side by side."

**Do:**

```bash
brew install gh pre-commit gitleaks azure-cli
gh auth login            # GitHub.com, HTTPS, "Login with a web browser"
git --version && python3 --version
mkdir -p ~/ebahn-project/dev/atelier && cd ~/ebahn-project/dev/atelier
```

Download the files from this chat into `~/Downloads/atelier-phase0/`, keeping their folder structure: the `atelier/` tree, the `atelier-env-fuhro/` tree and `SPEC.md`.

**You should see:** `gh auth status` says you are logged in as `atchiullia`.

**If not:** no Homebrew? Install it from brew.sh first. `gh auth login` stuck? Choose the browser option and paste the one-time code.

## Step 1: Create the three repositories (1 h)

**Say this:** "Three repos, split by how sensitive they are. The public one describes a generic edge. The private one holds everything that identifies my homelab. A second private one holds my photos and trend data."

**Do:**

```bash
cd ~/ebahn-project/dev/atelier
gh repo create atchiullia/atelier            --private --add-readme --license apache-2.0 --clone
gh repo create atchiullia/atelier-env-fuhro  --private --add-readme --clone
gh repo create atchiullia/atelier-brand-data --private --add-readme --clone
ls
```

The public repo starts **private** and stays private until Step 7.

**You should see:** three folders in `~/ebahn-project/dev/atelier`, and on github.com all three marked **Private**.

**If not:** "name already exists" means a repo with that name is already on your account; pick it up with `gh repo clone` instead.

## Step 2: The "only me" settings (1 h)

**Say this:** "The project is open to read and run, but nobody else can open pull requests. I also protect my own account, because with only one person allowed to merge, my account is the key to everything."

### 2a. Passkey on your account

github.com → your avatar → **Settings** → **Password and authentication** → **Passkeys** → **Add a passkey**. Use your Mac's Touch ID or a hardware key. Optionally keep authenticator-app 2FA as a backup.

### 2b. Sign your commits

```bash
ssh-keygen -t ed25519 -C "atchiullia signing key" -f ~/.ssh/id_ed25519_signing
ssh-add --apple-use-keychain ~/.ssh/id_ed25519_signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true
cat ~/.ssh/id_ed25519_signing.pub        # public key: safe to show
```

github.com → **Settings** → **SSH and GPG keys** → **New SSH key** → Key type **Signing Key** → paste the public key → **Add SSH key**.

### 2c. Settings on the `atelier` repo

Open github.com/atchiullia/atelier → **Settings**.

1. **General** → **Features**:
   - Find the **Pull requests** row. Keep the **Pull requests** checkbox ticked (unticking it disables pull requests entirely, and you still need them to run the required checks), then open the dropdown under it and choose **Collaborators only**. (GitHub moved this in 2026; it used to be a "Restrict pull requests to collaborators" option. If your page looks different, search the settings page for "collaborators".)
   - Untick **Issues**, **Wikis**, **Projects**, **Discussions**.
2. **Actions** → **General**:
   - **Approval for running fork pull request workflows from contributors** → **Require approval for all external contributors**.
   - **Workflow permissions** → **Read repository contents and packages permissions**; leave "Allow GitHub Actions to create and approve pull requests" **off**.

**You should see:** the new settings saved. The labels on GitHub may differ slightly in wording; the effect is what matters.

**If not:** on the GitHub Free plan, branch rules for **private** repos are not available. That is expected. We create them right after the repo goes public in Step 7.

**The real test comes in Step 7.** A stranger cannot even see a private repo, so "a test account cannot open a pull request" can only be proven once the repo is public.

## Step 3: Collect the private list (2 h)

**Say this:** "The leak guard needs to know what to look for: my internal names, addresses and IDs. A small tool finds most of them and writes them straight into the private repo. It prints counts only."

**Do:**

```bash
cd ~/ebahn-project/dev/atelier/atelier-env-fuhro
mkdir -p tools leak-patterns
cp ~/Downloads/atelier-phase0/atelier-env-fuhro/tools/collect-patterns.py tools/
cp ~/Downloads/atelier-phase0/atelier-env-fuhro/leak-patterns/README.md  leak-patterns/
```

Run it on a machine that is on your home network and has `kubectl` access to the Pi (the Pi itself, or your Mac if kubectl works from there). Check the context first, then run:

```bash
kubectl config current-context           # look at it, do not read it out loud
python3 tools/collect-patterns.py leak-patterns --local
```

The tool asks two questions (type `private`, then `fuhro`). It then prints something like `IP 3`, `CIDR 4`, `HOST 6`: **counts only**.

If `kubectl` only works on the Pi, copy the script there with `scp`, run it, `scp -r` the `leak-patterns/` folder back, then delete the copies on the Pi.

Now open the folder **in your editor with the camera off**, not in a shared terminal:

1. Read `patterns.txt` and ask yourself what is missing.
2. Open `suggestions.txt`. Move useful lines into `manual.txt` and delete the leading `# `. The zone suggestion looks like `[A-Za-z0-9-]+\.yourzone`: it flags *any subdomain* of the zone, and `allow.txt` already lets `ebahn.fuhro.network` through.
3. Work through the checklist in `leak-patterns/README.md` and add the rest to `manual.txt`. Add your Azure tenant ID and subscription ID as soon as you have them (Step 6).
4. Add a **canary**, a made-up word that exists only to prove the gate is alive:

```bash
printf 'CANARY\tzz-canary-%s\n' "$(openssl rand -hex 4)" >> leak-patterns/manual.txt
```

5. Commit to the private repo:

```bash
git add -A
git commit -m "Add leak-pattern tooling and first pattern list"
git push
git diff --stat HEAD~1                   # use --stat on camera, never the full diff
```

**You should see:** a short summary of counts, four files in `leak-patterns/`, and a successful push.

**If not:** "nothing collected" means `kubectl` points at the wrong cluster or cannot connect. Fix the context, run again.

## Step 4: Build the guards (4 h)

**Say this:** "Two checks. Gitleaks catches passwords and keys. My own checker, leakcheck, catches homelab details. It runs on my laptop before every commit and again in GitHub. If it complains it only says which file and line, never what it found, because the logs of a public repo are public."

### 4a. Copy the files into the public repo

```bash
cd ~/ebahn-project/dev/atelier/atelier
cp -R ~/Downloads/atelier-phase0/atelier/. .
cp ~/Downloads/atelier-phase0/SPEC.md .
ls -a
```

You should now have `tools/leakcheck/`, `.github/workflows/leak-gate.yml`, `.pre-commit-config.yaml`, `docs/adr/`, `docs/runbooks/` and the starter files. The `LICENSE` that GitHub created stays as it is.

### 4b. Install the hooks and run the tests

```bash
pre-commit autoupdate                    # pins gitleaks to the current release
pre-commit install
python3 -m unittest discover -s tools/leakcheck -v
python3 tools/leakcheck/leakcheck.py     # Tier 1 only: should print "0 finding(s)"
```

Now tell your shell where the private patterns are, so Tier 2 also runs locally:

```bash
echo 'export ATELIER_LEAK_PATTERNS="$HOME/ebahn-project/dev/atelier/atelier-env-fuhro/leak-patterns"' >> ~/.zshrc
source ~/.zshrc
python3 tools/leakcheck/leakcheck.py     # Tier 1 + Tier 2
```

**You should see:** `OK` from the tests, and `0 finding(s)` from both runs.

**If not:** each `LEAK <category> <file>:<line>` line needs a decision. Open that line and choose one:

- It is a real leak: remove it.
- It is a public fact (for example a public hostname): add a regex for it to `allow.txt` in the **private** repo.
- It is documentation that must mention something on purpose: add `leak-ok: <reason>` on the same line.

### 4c. Give GitHub read access to the pattern list

The CI job needs to read the private repo, using a token that can do nothing else.

github.com → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**:

- Name `atelier-ci-read-patterns`, expiration 90 days (put a reminder in your calendar).
- Resource owner: `atchiullia`. Repository access: **Only select repositories** → `atelier-env-fuhro`.
- Permissions → Repository permissions → **Contents: Read-only**.

Copy the token **with the camera off**, then store it as a secret without pasting it into any page:

```bash
gh secret set PATTERNS_TOKEN --repo atchiullia/atelier       # paste at the hidden prompt
```

### 4d. First commit on `main`

```bash
git add -A
git commit -m "Phase 0: spec, ADRs, leak gate, starter files"
git push -u origin main
gh run watch
```

**You should see:** the `leak-gate` workflow turn green with two jobs, `gitleaks` and `leakcheck`.

### 4e. Prove the gate works (the part viewers love)

Never test with a real secret. We use a made-up token and the canary.

```bash
git checkout -b test/leak-gate
CANARY=$(awk -F'\t' '$1=="CANARY"{print $2}' "$ATELIER_LEAK_PATTERNS/manual.txt" | head -1)
echo "$CANARY" > canary.txt
FAKE=$(python3 -c "import secrets,string;print('ghp_'+''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(36)))")
echo "token = $FAKE" > fake-secret.txt
git add canary.txt fake-secret.txt
git commit -m "test: this must be blocked"
```

**You should see (local):** the commit is **refused**. `leakcheck` prints `LEAK CANARY canary.txt:1` (no canary text), and gitleaks reports the fake token.

Now bypass the local hook on purpose, to prove CI is a second wall:

```bash
git commit --no-verify -m "test: bypass the local hook"
git push -u origin test/leak-gate
gh run watch
```

**You should see (CI):** both jobs fail. In the `leakcheck` log you see `LEAK CANARY canary.txt:1` and nothing else about the content.

Clean up:

```bash
git checkout main
git push origin --delete test/leak-gate
git branch -D test/leak-gate
git fetch --prune
```

GitHub may keep the test commits around for a while. That is why the test uses made-up values only.

**If not:** the gitleaks hook did not flag the fake token? Run `gitleaks --version`, and tell me; the canary part is the one that matters for this repo.

## Step 5: The decision notes (2 h)

**Say this:** "An ADR is a short note that says what I decided and why. Six months from now, or in an interview, this is how I remember my reasoning."

Already in the repo from Step 4: 0001 (monorepo), 0002 (two regions), 0011 (open source, guest tenant), 0014 (separate tunnel, with its two amendments) and 0016 (the leak gate).

**Do:**

1. Read each one. For every ADR, say out loud: what was the decision, what was the best alternative, and why did it lose?
2. Edit anything that does not match what you actually think. These are your decisions.
3. In ADR-0014 and ADR-0016, change **Proposed** to **Accepted** once you agree, and update the status in `SPEC.md` section 14.

```bash
git checkout -b adr-review
# edit the files, then:
git add -A && git commit -m "Review and accept ADRs 0001, 0002, 0011, 0014, 0016"
git push -u origin adr-review
gh pr create --fill
gh run watch
gh pr merge --squash --delete-branch
```

**You should see:** the checks pass on the pull request and the merge succeeds. Your first full pull request cycle on the repo.

## Step 6: The money alarm in Azure (2 h)

**Say this:** "A budget in Azure is an alarm, not a brake. It tells me when spending crosses a line; it does not stop anything. The brake comes later, as automation."

### 6a. Subscription

```bash
az login
az account show --query "{name:name, state:state}" -o table      # do not show IDs on camera
```

No subscription yet? Create one at azure.microsoft.com/free (a free account has credits and a built-in spending limit) or a pay-as-you-go one. Then add the **tenant ID** and **subscription ID** to `manual.txt` in the private repo, so the leak gate protects them.

### 6b. Notification path first

Azure portal → **Monitor** → **Alerts** → **Action groups** → **Create**:

- Name `ag-atelier-budget`, short name `atelier`, region **Global**.
- Notifications → **Email/SMS message/Push/Voice** → Email → your address.
- **Create**, open it, then press **Test action group** → Email → **Test**.

**You should see:** the test email arrives. That proves the alarm can reach you.

### 6c. The budget

Portal → **Cost Management** → **Budgets** → **+ Add**:

- Scope: your subscription. Name `atelier-monthly-40`. Reset period **Monthly**. Amount **40**.
- Alert conditions, all pointing at `ag-atelier-budget` and your email:
  - **Actual** 50 percent
  - **Actual** 80 percent
  - **Forecasted** 100 percent
  - **Actual** 100 percent
- **Create**.

**You should see:** the budget listed with its four alerts.

**If not / good to know:** Azure evaluates budgets on a delay of up to about a day, so a fresh subscription will not alert quickly. The Step 6b test email is how you verify the path today. In Phase 5 we add the automation that scales the cluster to zero when an alert fires.

## Step 7: History check, go public, write-up (2 h)

**Say this:** "Once a repo is public, everything in its history is public too. So before the switch I scan every commit ever made. Then I flip it, lock the front door and check that a stranger really cannot open a pull request."

### 7a. Scan all of history

```bash
cd ~/ebahn-project/dev/atelier/atelier
git fetch --prune
python3 tools/leakcheck/leakcheck.py --history
gitleaks git --redact .            # older versions: gitleaks detect --redact
```

**You should see:** `0 finding(s)` and no gitleaks leaks.

**If not:** a finding in an old commit means history must be rewritten before going public. Stop and tell me; do not flip the switch. (The repo is still private and young, so the simplest fix is usually to recreate it from a clean copy.)

### 7b. Final checklist before flipping

- [ ] `README.md`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` are present.
- [ ] No brand photos or trend data anywhere (those belong in `atelier-brand-data`).
- [ ] No homelab overlay, no tunnel or WireGuard files.
- [ ] The latest `leak-gate` run on `main` is green.

### 7c. Flip it

github.com/atchiullia/atelier → **Settings** → **General** → bottom of the page → **Danger Zone** → **Change visibility** → **Make public**. Or:

```bash
gh repo edit atchiullia/atelier --visibility public --accept-visibility-change-consequences
```

### 7d. Lock the front door (right after the flip)

1. **Settings** → **Rules** → **Rulesets** → **New ruleset** → **New branch ruleset**:
   - Name `protect-main`, Enforcement **Active**, Target **Default branch**.
   - Tick: **Restrict deletions**, **Block force pushes**, **Require signed commits**, **Require a pull request before merging** (required approvals **0**, because you are the only maintainer), **Require status checks to pass** → add `gitleaks` and `leakcheck`.
   - Leave the bypass list empty.
2. **Settings** → **Code security** → **Private vulnerability reporting** → **Enable**.
3. Re-check **Settings → General → Features** (pull requests restricted) and **Settings → Actions → General** (approval for all external contributors).
4. Repo page: add a short description and topics (`kubernetes`, `platform-engineering`, `ecommerce`, `gitops`).

### 7e. The stranger test (this is the exit criterion)

Open the repo page in a private window where you are signed out, or sign in with a second GitHub account.

- The **Pull requests** tab shows no way to create a new one, or creating one is refused.
- A fork of the repo cannot open a pull request back.
- Actions on the fork do not run without approval.

**You should see:** a refusal each time. This is the "done when" for the whole step.

### 7f. Write-up and CV line

**"What I built / what broke / what I learned"** (5 sentences, for LinkedIn or a video description):

1. What: a public repo for my platform project, with a private twin for everything that identifies my homelab.
2. How: a leak checker that runs before every commit and again in GitHub, and only ever reports file and line.
3. What broke or surprised me: (fill in; for example a false positive, or the fact that a budget is only an alarm).
4. What I learned: public CI logs are public, so the guard must never print what it finds; and a gate that quietly loads nothing is worse than no gate, so mine fails closed.
5. Next: Phase 1, running the platform as an isolated guest on my Pi.

**CV bullet** (codes SEC, DOC, CICD):

> Designed an open-source repo security model for a Kubernetes platform: public/private repository split, a custom fail-closed leak scanner with redacted output in pre-commit and CI alongside gitleaks, a closed-contribution GitHub policy, and an Azure budget alarm; verified with canary tests.

## Phase 0 is done when

- [ ] Three repos exist; the public one is public, the other two private.
- [ ] A stranger cannot open a pull request (Step 7e).
- [ ] The canary commit is blocked locally and in CI, and the log never shows its text.
- [ ] A made-up token is caught by gitleaks.
- [ ] The Azure test email arrived and the $40 budget exists.
- [ ] ADRs reviewed and accepted; `SPEC.md` status updated.
- [ ] Write-up and CV bullet saved.

## You should be able to explain, without notes

1. Why there are three repos, and what goes in each.
2. Why the guard prints only file and line.
3. What "fail closed" means and why a silent, empty gate is dangerous.
4. Why a leaked secret in history must be rotated, not just deleted.
5. Why a budget alert is not a spending limit.
6. Why we never use `pull_request_target` here, and why closing the contribution door is simpler than defending it.
7. What a canary is for.

## Next: Phase 1

Check the Pi's memory and disk, give Atelier its own rooms with hard limits, add rules that keep it apart from your internal apps, and bring up the first `hello` page at `ebahn.fuhro.network` through its own tunnel.
