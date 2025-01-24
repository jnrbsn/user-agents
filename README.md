# jnrbsn/user-agents

Latest user agent strings for major browsers and OSs; checks for updates daily:

<https://jnrbsn.github.io/user-agents/user-agents.json>

## Update 2025-01-23

**TL;DR:** I made it better, more correct, and more reliable! :tada:

When I created this repo around 4.5 years ago, it originally screen-scraped the
user agent strings from [whatismybrowser.com][1]. Around two years ago, that
website blocked GitHub Actions. So then I thought I had a clever idea of using
[The Internet Archive][2] and also making it take regular snapshots. But then,
because of legal problems, The Internet Archive was temporarily shutdown for a
month last year. Regardless of the shutdown, the GitHub Action just fails
sometimes for various reasons. It has become fragile and complex, and I don't
like it. I also learned, as I was researching the rewrite of this, that some of
the user agent strings on whatismybrowser.com are not even valid/correct.
They're obviously generating their strings using outdated rules.

Meanwhile, in the years since I created this repo, the state of the browser
user agent string has changed in significant ways. Driven by frustration with
constant user-agent-sniffing bugs, as well as a desire to reduce browser
fingerprinting, every major browser now hard-codes most of its user agent
string. There are now fixed strings for macOS, Windows, and Linux, and things
like CPU architectures and engine versions are now fixed as well.

* **Chrome:** In Chromium, the user agent string is now [well-documented][3].
  On the desktop version, the only parts that aren't fixed are the OS/platform
  (which can only be one of a handful of fixed strings) and the major version
  of Chromium (the minor parts of the version are hard-coded as zeros).
* **Firefox:** The [macOS version][4] and [Windows version][5] are now fixed in
  Firefox, and the [CPU architecture][6] is now hard-coded for all OSs. On
  Linux, the OS part of the user agent is usually just generic anyway, with a
  hard-coded [special case for Ubuntu][7]. Also, the [Gecko version][8] has
  been fixed for many years on desktop.
* **Safari:** In WebKit, the [macOS version][9] and the [WebKit version][10]
  are now fixed. The only thing that Safari adds to the WebKit user agent is
  the Safari version at the end.
* **Edge:** Edge is based on Chromium and mostly uses the same user agent
  string, but it adds the [major version of Edge at the end][11], which
  somewhat amusingly, is the same as the major version of Chromium.

So now, instead of using fragile methods of screen-scraping a website of
dubious quality, I get the latest major version of each of the above browsers
from official sources and then generate the following 16 user agent strings:

* two most-recent versions of Chrome on macOS, Windows, and Linux (Chrome rolls
  out releases very gradually, so it's common to have many users on the
  previous version) (6 strings)
* latest and ESR (extended support release) versions of Firefox on macOS,
  Windows, generic Linux, and Ubuntu (8 strings)
* latest version of Safari on macOS
* latest version of Edge on Windows

[1]: https://www.whatismybrowser.com/guides/the-latest-user-agent/
[2]: https://web.archive.org/
[3]: https://www.chromium.org/updates/ua-reduction/
[4]: https://hg.mozilla.org/mozilla-central/rev/ba73a7622f6366fa1c1446fa96d42b93166d91e0
[5]: https://hg.mozilla.org/mozilla-central/rev/fbbdeef57f8252daf5400305c289119c73382942
[6]: https://bugzilla.mozilla.org/show_bug.cgi?id=1559747
[7]: https://hg.mozilla.org/mozilla-central/rev/2d4419b5c1dfb8d6ae096cfb5c01dc75f33dffe8
[8]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox
[9]: https://github.com/WebKit/WebKit/commit/49a2b0400d3f6a16e8d604e112da4b38d22cbd02
[10]: https://github.com/WebKit/WebKit/commit/1a54b3453655e45af52850475f50fc01de2fe710
[11]: https://learn.microsoft.com/en-us/microsoft-edge/web-platform/user-agent-guidance#user-agent-strings
