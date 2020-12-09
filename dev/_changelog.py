"""Create pyRevit change log"""
# pylint: disable=invalid-name,broad-except
import re
import logging
from typing import Dict
from collections import namedtuple, defaultdict

# dev scripts
from scripts import utils
from scripts import github


logger = logging.getLogger()


ChangeGroup = namedtuple("ChangeGroup", ["tag", "header"])


class Change:
    """Type representing a commit point"""

    def __init__(self, commit_hash, message, comments):
        self.commit_hash = commit_hash
        self.message = message
        self.comments = comments

        # parse message for type and ticket #
        self.issue_type = "commit"
        self._ticket = ""
        self._parse_message()

        # parse message for change group
        # cleans up message from group tags
        self.groups = []
        self._find_groups()

        # find todo items in commit comments
        self.todos = []
        self._find_todos()

        # if ticket number found in message
        # get ticket info from cloud
        self._ticketdata = None
        if self._ticket:
            self._getinfo()

    def _parse_message(self):
        # determine type from message
        # find prs
        if m := re.match(r".*pr\/(\d+).*", self.message):
            self._ticket = m.groups()[0]
            self.issue_type = "pr"
        # find issues
        elif m := re.match(r".*#(\d+).*", self.message):
            self._ticket = m.groups()[0]
            if "merge" in self.message.lower():
                self.issue_type = "pr"
            else:
                self.issue_type = "issue"

    def _find_groups(self):
        if gtags := re.findall(r"\[(.+?)\]", self.message):
            # clean the tags from change message
            for gtag in gtags:
                self.message = self.message.replace(f'[{gtag}]', '')
            self.message = self.message.strip()
            self.message = re.sub(r'\s+', ' ', self.message)
            self.groups = gtags

    def _find_todos(self):
        for cline in self.comments.split('\n'):
            if m := re.search(r'\-\s*\[\s*\]\s+(.+)', cline):
                self.todos.append(m.groups()[0])

    def _getinfo(self):
        if self._ticket:
            self._ticketdata = github.get_ticket(self._ticket)

    @property
    def ticket(self):
        """Ticket #"""
        return f"#{self._ticket}"

    @property
    def url(self):
        """Ticket url"""
        if self._ticketdata:
            return self._ticketdata.url

    @property
    def title(self):
        """Ticket title"""
        if self._ticketdata:
            return self._ticketdata.title


CHANGE_GROUPS = [
    ChangeGroup(tag="tool", header="Tools"),
    ChangeGroup(tag="host", header="Supported Revits"),
    ChangeGroup(tag="engine", header="Engines"),
    ChangeGroup(tag="runtime", header="Runtime"),
    ChangeGroup(tag="framework", header="Framework Updates"),
    ChangeGroup(tag="installer", header="Installer"),
    ChangeGroup(tag="cli", header="Command Line Utility"),
    ChangeGroup(tag="bundles", header="Script bundles"),
    ChangeGroup(tag="tele", header="Telemetry"),
    ChangeGroup(tag="api", header="API"),
    ChangeGroup(tag="", header="Misc Changes"),
]

SKIP_PATTERNS = [r"cleanup", r"^Merge branch \'.+\' into .+$"]


def find_changes(gitlog_report: str):
    """Create changes from git log report"""
    # designed to work with `git log --pretty='format:%h %s%n%b/'`
    changes = []
    idx = 0
    changelines = gitlog_report.split("\n")
    while idx < len(changelines):
        # extract hash and message
        cline = changelines[idx]
        chash, cmsg = cline.split(" ", 1)
        logger.debug('commit -> %s: %s', chash, cmsg)
        # grab all the comments lines
        idx += 1
        ccmt = ""
        cline = changelines[idx]
        while not cline.startswith("/"):
            ccmt += cline
            idx += 1
            cline = changelines[idx]
        # add a new change
        changes.append(
            Change(commit_hash=chash, message=cmsg, comments=ccmt)
            )
        idx += 1
    return changes


def header(text: str, level: int = 2):
    """Print markdown header"""
    print("#" * level + f" {text}")


def report_clog(args: Dict[str, str]):
    """Report changes from given <tag> to HEAD
    Queries github issue information for better reporting
    """
    tag_hash = utils.system(["git", "rev-parse", f"{args['<tag>']}"])
    gitlog_report = utils.system(
        ["git", "log", "--pretty=format:%h %s%n%b/", f"{tag_hash}..HEAD"]
    )
    changes = find_changes(gitlog_report)

    # groups changes (and purge)
    grouped_changes = defaultdict(list)
    for change in changes:
        # skip unintersting commits
        if any(re.search(x, change.message) for x in SKIP_PATTERNS):
            continue

        if change.groups:
            for group in change.groups:
                grouped_changes[group].append(change)
        else:
            grouped_changes[""].append(change)

    # report changes by groups in order
    for cgroup in CHANGE_GROUPS:
        header(cgroup.header, level=1)
        for change in grouped_changes[cgroup.tag]:
            if change.issue_type == 'issue':
                print(f"- Resolved Issue ({change.ticket}: {change.title})")
            elif change.issue_type == 'pr':
                print(f"- Merged PR ({change.ticket}: {change.title})")
            else:
                print(f"- {change.message}")

            for todo in change.todos:
                print(f'    - [ ] {todo}')
