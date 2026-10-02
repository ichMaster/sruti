# sruti

A listening agent: it tunes into a public WebSDR receiver, reads the Morse code (CW) it hears as text, and
explains it in real time in a four-section terminal interface — the original text, a word-by-word gloss
and the message translated into English (a local LLM, per piece), and, at the push of a button, an
explanation in Ukrainian of what is going on (Claude Opus 5.5). Every listening session is saved and can
be reopened; switching the session is retuning. A web interface on localhost follows in v2.

*Śruti* is Sanskrit for "that which is heard".

**Status:** specification. Start with [specification/MISSION.md](specification/MISSION.md), then
[ARCHITECTURE.md](specification/ARCHITECTURE.md) and [ROADMAP.md](specification/ROADMAP.md).

## License

[MIT](LICENSE)
