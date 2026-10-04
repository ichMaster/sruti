import pytest

from sruti.cli import build_parser


def test_listen_contract_arguments():
    args = build_parser().parse_args(["listen", "--receiver", "sdr.example.org:8073", "--freq", "7027.5"])
    assert (args.command, args.receiver, args.freq) == ("listen", "sdr.example.org:8073", 7027.5)


@pytest.mark.parametrize("argv", [
    ["listen", "--receiver", "sdr.example.org:8073", "--freq", "50"],
    ["listen", "--receiver", "sdr.example.org:8073", "--freq", "40000"],
    ["listen", "--receiver", "no-port", "--freq", "7027.5"],
    ["listen", "--freq", "7027.5"],
    ["listen", "--receiver", "sdr.example.org:8073"],
    [],
])
def test_listen_rejects_bad_arguments(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(argv)
    assert exc.value.code == 2


def test_help_shows_the_contract(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["listen", "--help"])
    out = capsys.readouterr().out
    assert "--receiver" in out and "--freq" in out
