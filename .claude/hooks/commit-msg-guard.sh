#!/bin/bash
# commit-msg-guard.sh — Block forbidden trailers and headings in commits and PRs
# Trigger: Bash(git commit *), Bash(gh pr create *)
# Action: deny JSON (PreToolUse)
# Input: tool_input JSON on stdin
#
# Only a real `git commit` or `gh pr create` (the program at a command
# position, outside quotes and heredoc bodies, found by the jq lexer below) is
# checked; any other command that merely mentions a trailer passes.

read -r -d '' lexer <<'JQ' || true
# >>> shared command lexer: keep byte-identical in commit-msg-guard.sh and commit-prefix-guard.sh
# Splits a Bash command into simple commands ({w: words, hd: heredoc body,
# pin: stdin piped from the previous one}) the way the shell would: separators
# and "#" count only outside quotes and heredoc bodies, and quotes are removed.
def rx: gsub("(?<c>[^A-Za-z0-9_])"; "\\\(.c)");
def addw($v): .cur = ((.cur // "") + $v);
def endw: if .cur == null then . else (.segs | length - 1) as $k | .segs[$k].w += [.cur] | .cur = null end;
def endseg($op): endw | .segs += [{w: [], hd: null, pin: ($op == "|" or $op == "|&")}];
def unesc: gsub("\\\\\n"; "") | gsub("\\\\(?<c>[\"\\\\$`])"; .c);
def cap($re): [capture("\\A(?<all>" + $re + ")")] | .[0];
def heredoc($r):
  .pend[0] as $p
  | ($r | cap("\n(?:(?<b>[\\s\\S]*?)\n)?" + (if $p.t then "\t*" else "" end) + $p.re + "(?=\n|\\z)")) as $m
  | (if $m == null then {all: $r, b: $r[1:]} else $m end) as $m
  | .segs[$p.seg].hd = ($m.b // "" | if $p.t then split("\n") | map(sub("\\A\t+"; "")) | join("\n") else . end)
  | .pend = .pend[1:] | .i += ($m.all | length);
def rules: [
  ["ws", "[ \t\r\f\u000b]+|\\\\\n"], ["com", "#[^\n]*"],
  ["op", "\n|&&|\\|\\||;;|;|\\|&|\\||&(?!>)|\\(|\\)"],
  ["redir", "<<<|[0-9]*(?:&>>?|>&|<&|>>?|<>?)(?!<)(?:[0-9]+-?|-)?"],
  ["hdoc", "<<(?<d>-?)[ \t]*(?:'(?<q>[^']*)'|\"(?<qq>[^\"]*)\"|\\\\?(?<b>[^\\s;&|<>()'\"]+))"],
  ["sq", "'(?<v>[^']*)'?"],
  ["ansi", "\\$'(?<v>(?:\\\\[\\s\\S]|[^'\\\\])*)'?"],
  ["cat", "\"\\$\\(\\s*cat\\s*<<-?\\s*['\"]?(?<d>\\w+)['\"]?[ \t]*\n(?<v>[\\s\\S]*?)\n\\s*\\k<d>\\s*\\)\\s*\""],
  ["dq", "\"(?<v>(?:\\\\[\\s\\S]|\\$\\((?:[^()'\"]|'[^']*'|\"(?:\\\\[\\s\\S]|[^\"\\\\])*\")*\\)|[^\"\\\\])*)\"?"],
  ["esc", "\\\\(?<v>[\\s\\S])"],
  ["word", "\\$\\((?:[^()'\"]|'[^']*'|\"(?:\\\\[\\s\\S]|[^\"\\\\])*\"|\\([^()]*\\))*\\)|[^\\s'\"\\\\;&|()<>$#]+|[\\s\\S]"]];
def step($r):
  if ($r | startswith("\n")) and (.pend | length) > 0 then heredoc($r)
  else .cur as $cur
  | first(rules[] as [$k, $re] | $r | cap($re) | select(. != null and ($k != "com" or $cur == null)) | .k = $k) as $m
  | .i += ($m.all | length)
  | if $m.k == "ws" or $m.k == "com" then endw
    elif $m.k == "op" then endseg($m.all)
    elif $m.k == "redir" then endw | addw($m.all) | endw
    elif $m.k == "hdoc" then endw | .pend += [{seg: (.segs | length - 1), t: ($m.d == "-"), re: ($m.q // $m.qq // $m.b | rx)}]
    elif $m.k == "ansi" then addw($m.v | gsub("\\\\n"; "\n") | gsub("\\\\t"; "\t") | gsub("\\\\(?<c>['\"\\\\])"; .c))
    elif $m.k == "dq" then addw($m.v | unesc)
    elif $m.v != null then addw($m.v)
    else addw($m.all) end
  end;
def lex:
  . as $s | ($s | length) as $n
  | {i: 0, cur: null, pend: [], segs: [{w: [], hd: null, pin: false}]}
  | until(.i >= $n; step($s[.i:])) | endw | .segs;
# Words of a simple command from its program on, past leading VAR=value words.
def prog: . as $w | ([range(0; $w | length) | select($w[.] | test("\\A[A-Za-z_][A-Za-z0-9_]*=") | not)] | .[0] // ($w | length)) as $k | $w[$k:];
# git's subcommand and its arguments, past git's own options such as -C <dir>.
def gitsub: prog | select((.[0] // "") | test("(\\A|/)git\\z")) | . as $w
  | {k: 1} | until(($w[.k] // "") | startswith("-") | not;
      .k += (if $w[.k] | test("\\A(-C|-c|--git-dir|--work-tree|--namespace|--config-env)\\z") then 2 else 1 end))
  | $w[.k:];
def is_commit: [gitsub | .[0] == "commit"] | any;
def is_pr_create: prog | ((.[0] // "") | test("(\\A|/)gh\\z")) and .[1] == "pr" and .[2] == "create";
# The message of simple command $j in $s: {kind: "m", v: text}, {kind: "f", v: path} or {kind: "n"} (none found).
def commit_msg($s; $j):
  ($s[$j].hd // (if $s[$j].pin and $j > 0 then $s[$j - 1].hd else null end)) as $in
  | ($s[$j].w | [gitsub] | .[0][1:]) as $a
  | {k: 0, m: [], f: null}
  | until(.k >= ($a | length);
      $a[.k] as $x
      | if $x == "--" then .k = ($a | length)
        elif $x == "-m" or $x == "--message" then .m += [$a[.k + 1] // ""] | .k += 2
        elif $x | startswith("--message=") then .m += [$x[10:]] | .k += 1
        elif $x == "--file" then .f = $a[.k + 1] | .k += 2
        elif $x | startswith("--file=") then .f = $x[7:] | .k += 1
        elif $x | test("\\A-(?!-)[^mFCct]*[mFCct]") then
          ($x | capture("\\A-[^mFCct]*(?<o>[mFCct])(?<v>[\\s\\S]*)")) as $o
          | (if $o.v != "" then $o.v else $a[.k + 1] // "" end) as $v
          | (if $o.o == "m" then .m += [$v] elif $o.o == "F" then .f = $v else . end)
          | .k += (if $o.v != "" then 1 else 2 end)
        else .k += 1 end)
  | if (.m | length) > 0 then {kind: "m", v: (.m | join("\n\n"))}
    elif .f == "-" then (if $in != null then {kind: "m", v: $in} else {kind: "n"} end)
    elif .f != null then {kind: "f", v: .f}
    else {kind: "n"} end;
# <<< shared command lexer
JQ

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
case "$cmd" in *git*commit*|*gh*pr*create*) ;; *) exit 0;; esac

gated=$(printf '%s' "$input" | jq -r "$lexer"'
  [.tool_input.command // "" | lex[] | .w | is_commit or is_pr_create] | any')
[ "$gated" = true ] || exit 0

if echo "$cmd" | grep -qiE 'Co-Authored-By|Generated with Claude Code' ||
   echo "$cmd" | grep -qE '##[[:space:]]*Test [Pp]lan'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: forbidden trailer/heading. Remove Co-Authored-By, Generated-with, and Test plan sections."}}'
fi
