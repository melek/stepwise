// Stepwise paper-ID normalization — companion to canonical_key() in
// lib/postconditions.py.
//
// Issue #17 was a matching bug: the snowball log and included.jsonl named
// the same paper in different forms. The tests sample those forms; these
// lemmas cover every string: a scheme prefix, letter case, or an arXiv
// version suffix never changes the key, and distinct plain IDs never
// collide. Whitespace trimming is not modelled; inputs are assumed trimmed.

function LowerChar(c: char): char
{
  if 'A' <= c <= 'Z' then (c as int - 'A' as int + 'a' as int) as char else c
}

function Lower(s: string): string
  ensures |Lower(s)| == |s|
{
  seq(|s|, i requires 0 <= i < |s| => LowerChar(s[i]))
}

// Same order as _ID_PREFIXES: the first match is stripped, once.
const Prefixes: seq<string> := [
  "https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/",
  "doi:", "s2:", "arxiv:"
]

function StripFrom(s: string, i: nat): string
  requires i <= |Prefixes|
  decreases |Prefixes| - i
{
  if i == |Prefixes| then s
  else if Prefixes[i] <= s then s[|Prefixes[i]|..]
  else StripFrom(s, i + 1)
}

function StripPrefix(s: string): string
{
  StripFrom(s, 0)
}

predicate IsDigit(c: char) { '0' <= c <= '9' }

predicate AllDigits(s: string) { forall i :: 0 <= i < |s| ==> IsDigit(s[i]) }

// yymm.nnnn or yymm.nnnnn
predicate ArxivBase(b: string)
{
  (|b| == 9 || |b| == 10) && AllDigits(b[..4]) && b[4] == '.' && AllDigits(b[5..])
}

// Mirrors _ARXIV_VERSION = ^(\d{4}\.\d{4,5})v\d+$
function StripVersion(s: string): string
{
  if |s| >= 11 && ArxivBase(s[..9]) && s[9] == 'v' && AllDigits(s[10..]) then s[..9]
  else if |s| >= 12 && ArxivBase(s[..10]) && s[10] == 'v' && AllDigits(s[11..]) then s[..10]
  else s
}

function Key(s: string): string
{
  StripVersion(StripPrefix(Lower(s)))
}

predicate HasPrefix(s: string)
{
  exists i :: 0 <= i < |Prefixes| && Prefixes[i] <= s
}

// An ID already in plain form: lowercase, unprefixed, unversioned.
predicate Plain(s: string)
{
  Lower(s) == s && !HasPrefix(s) && StripVersion(s) == s
}

// ---- Helper lemmas ----

lemma LowerIdempotent(s: string)
  ensures Lower(Lower(s)) == Lower(s)
{
}

lemma StripFromNoMatch(s: string, i: nat)
  requires i <= |Prefixes|
  requires forall j :: i <= j < |Prefixes| ==> !(Prefixes[j] <= s)
  ensures StripFrom(s, i) == s
  decreases |Prefixes| - i
{
  if i < |Prefixes| {
    StripFromNoMatch(s, i + 1);
  }
}

lemma PrefixesLowercase(k: int)
  requires 0 <= k < |Prefixes|
  ensures Lower(Prefixes[k]) == Prefixes[k]
{
}

lemma LowerConcat(a: string, b: string)
  ensures Lower(a + b) == Lower(a) + Lower(b)
{
}

lemma NotPrefixAt(a: string, b: string, i: int)
  requires 0 <= i < |a| && i < |b| && a[i] != b[i]
  ensures !(a <= b)
{
}

// The prefix list is prefix-free: no entry is a prefix of another.
// One witness per pair (generated: first differing character).
lemma PrefixFree(j: int, k: int)
  requires 0 <= j < |Prefixes| && 0 <= k < |Prefixes| && j != k
  ensures !(Prefixes[j] <= Prefixes[k])
{
  if j == 0 && k == 2 { NotPrefixAt(Prefixes[j], Prefixes[k], 9); }
  if j == 0 && k == 3 { NotPrefixAt(Prefixes[j], Prefixes[k], 4); }
  if j == 1 && k == 0 { NotPrefixAt(Prefixes[j], Prefixes[k], 4); }
  if j == 1 && k == 2 { NotPrefixAt(Prefixes[j], Prefixes[k], 4); }
  if j == 1 && k == 3 { NotPrefixAt(Prefixes[j], Prefixes[k], 8); }
  if j == 3 && k == 2 { NotPrefixAt(Prefixes[j], Prefixes[k], 4); }
  if j == 4 && k == 0 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 4 && k == 1 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 4 && k == 2 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 4 && k == 3 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 4 && k == 6 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 5 && k == 0 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 5 && k == 1 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 5 && k == 2 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 5 && k == 3 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 5 && k == 4 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 5 && k == 6 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 6 && k == 0 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 6 && k == 1 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 6 && k == 2 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
  if j == 6 && k == 3 { NotPrefixAt(Prefixes[j], Prefixes[k], 0); }
}

// No listed prefix is a prefix of another, so P + x can only match P.
lemma OnlyOwnPrefixMatches(k: int, j: int, x: string)
  requires 0 <= k < |Prefixes| && 0 <= j < |Prefixes| && j != k
  ensures !(Prefixes[j] <= Prefixes[k] + x)
{
  var p, q := Prefixes[k], Prefixes[j];
  if q <= p + x {
    if |q| <= |p| {
      assert q == (p + x)[..|q|] == p[..|q|];
      PrefixFree(j, k);
    } else {
      assert p == (p + x)[..|p|] == q[..|p|];
      PrefixFree(k, j);
    }
  }
}

lemma StripsOwnPrefix(k: int, x: string, i: nat)
  requires 0 <= k < |Prefixes| && i <= k
  requires !HasPrefix(x)
  ensures StripFrom(Prefixes[k] + x, i) == x
  decreases k - i
{
  if i < k {
    OnlyOwnPrefixMatches(k, i, x);
    StripsOwnPrefix(k, x, i + 1);
  } else {
    assert Prefixes[k] <= Prefixes[k] + x;
    assert (Prefixes[k] + x)[|Prefixes[k]|..] == x;
  }
}

// ---- Matching properties ----

// Letter case never changes the key (DOIs are case-insensitive).
lemma CaseInvariant(s: string)
  ensures Key(Lower(s)) == Key(s)
{
  LowerIdempotent(s);
}

// `s2:abc`, `doi:abc`, `https://doi.org/abc` ... all key the same as `abc`.
// This is the shape #17 was reopened for.
lemma PrefixInvariant(k: int, x: string)
  requires 0 <= k < |Prefixes|
  requires Lower(x) == x && !HasPrefix(x)
  ensures Key(Prefixes[k] + x) == Key(x)
{
  LowerConcat(Prefixes[k], x);
  PrefixesLowercase(k);
  StripsOwnPrefix(k, x, 0);
  StripFromNoMatch(x, 0);
}

// Distinct plain IDs never collide: normalization can't merge two papers.
lemma NoFalseMerge(x: string, y: string)
  requires Plain(x) && Plain(y)
  requires Key(x) == Key(y)
  ensures x == y
{
  StripFromNoMatch(x, 0);
  StripFromNoMatch(y, 0);
}

lemma LowerNoUpper(s: string)
  requires forall i :: 0 <= i < |s| ==> !('A' <= s[i] <= 'Z')
  ensures Lower(s) == s
{
}

// Every listed prefix starts with a letter, so an ID starting with a digit
// has no prefix to strip.
lemma DigitStartHasNoPrefix(s: string)
  requires |s| > 0 && IsDigit(s[0])
  ensures !HasPrefix(s)
{
  forall i | 0 <= i < |Prefixes|
    ensures !(Prefixes[i] <= s)
  {
    NotPrefixAt(Prefixes[i], s, 0);
  }
}

// `2301.01234v2` keys the same as `2301.01234`.
lemma VersionInvariant(b: string, n: string)
  requires ArxivBase(b) && |n| > 0 && AllDigits(n)
  ensures Key(b + "v" + n) == Key(b)
{
  var s := b + "v" + n;
  LowerNoUpper(s);
  LowerNoUpper(b);
  DigitStartHasNoPrefix(s);
  DigitStartHasNoPrefix(b);
  StripFromNoMatch(s, 0);
  StripFromNoMatch(b, 0);
  assert s[..|b|] == b && s[|b|] == 'v' && s[|b| + 1..] == n;
}
