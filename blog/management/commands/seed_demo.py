"""Populate an empty install with topics and a few finished example posts.

    python manage.py seed_demo            # add what is missing
    python manage.py seed_demo --flush    # delete demo content first

Safe to re-run: everything is looked up by slug before being created.
"""

import textwrap

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from blog.models import Category, Post, Tag

CATEGORIES = [
    {
        "name": "Computer Science",
        "icon": "💻",
        "color": "#4f46e5",
        "tagline": "Algorithms, systems and the code that makes them real.",
        "description": "Data structures, complexity, compilers, databases and distributed systems — "
        "explained with code you can run.",
        "position": 1,
    },
    {
        "name": "Physics",
        "icon": "⚛",
        "color": "#0ea5e9",
        "tagline": "From classical mechanics to quantum weirdness.",
        "description": "Derivations done in full, with the physical intuition that textbooks leave out.",
        "position": 2,
    },
    {
        "name": "Mathematics",
        "icon": "∑",
        "color": "#db2777",
        "tagline": "The machinery behind everything else.",
        "description": "Linear algebra, analysis, probability and the proofs worth knowing.",
        "position": 3,
    },
    {
        "name": "Economics",
        "icon": "📈",
        "color": "#059669",
        "tagline": "Models, markets and what the data actually says.",
        "description": "Micro, macro and econometrics, with real datasets instead of hand-waving.",
        "position": 4,
    },
    {
        "name": "Machine Learning",
        "icon": "🧠",
        "color": "#d97706",
        "tagline": "The mathematics under the hype.",
        "description": "Gradient descent, transformers and evaluation done honestly.",
        "position": 5,
    },
    {
        "name": "Engineering",
        "icon": "🛠",
        "color": "#7c3aed",
        "tagline": "Building things that keep working.",
        "description": "Tooling, deployment, testing and the unglamorous parts that decide outcomes.",
        "position": 6,
    },
]

POSTS = [
    {
        "title": "Binary search is harder than it looks",
        "subtitle": "Four lines of code, one of the most commonly mis-implemented algorithms in the field.",
        "category": "Computer Science",
        "tags": ["algorithms", "python", "invariants"],
        "featured": True,
        "content": textwrap.dedent(
            '''
            Binary search is the first algorithm most people meet after linear search, and the
            last one they get right. The idea takes a sentence; the implementation hides three
            separate off-by-one traps.

            ## The idea

            Keep a window of the array that *could* contain the target. Every comparison halves
            it. When the window is empty, the target is not there.

            The part that matters is the **invariant**: everything outside `[lo, hi]` has already
            been ruled out. Write the invariant down before you write the loop and the off-by-ones
            disappear.

            ## A version that works

            ```python
            def binary_search(items, target):
                """Return the index of target in sorted items, or -1."""
                lo, hi = 0, len(items) - 1          # invariant: answer, if any, is in [lo, hi]
                while lo <= hi:
                    mid = lo + (hi - lo) // 2       # no overflow, even in fixed-width ints
                    if items[mid] == target:
                        return mid
                    if items[mid] < target:
                        lo = mid + 1                # everything up to mid is too small
                    else:
                        hi = mid - 1                # everything from mid up is too large
                return -1
            ```

            Three details are doing real work:

            1. `while lo <= hi`, not `<`. With `<`, a one-element window is never examined.
            2. `mid = lo + (hi - lo) // 2`. In Python integers are unbounded so `(lo + hi) // 2`
               is fine, but in C, Java or Rust that addition overflows for large arrays — the bug
               that sat in the JDK's own implementation for nine years.
            3. `mid + 1` and `mid - 1`. Assigning `lo = mid` when `mid == lo` loops forever.

            ## The version you actually want

            Most real uses are not "is it there?" but "where does it belong?". That is the
            *lower bound*: the first index whose value is not less than the target.

            ```python
            def lower_bound(items, target):
                """First index i where items[i] >= target (may equal len(items))."""
                lo, hi = 0, len(items)              # note: half-open window [lo, hi)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if items[mid] < target:
                        lo = mid + 1
                    else:
                        hi = mid
                return lo
            ```

            This one never returns "not found" — it returns an insertion point, which is strictly
            more useful. Membership becomes a follow-up check:

            ```python
            i = lower_bound(items, target)
            found = i < len(items) and items[i] == target
            ```

            !!! note "Use the standard library"
                In Python, `bisect.bisect_left` is exactly `lower_bound`, written in C. Write your
                own to understand it; ship the library version.

            ## Testing it properly

            Hand-picked examples miss exactly the cases that break binary search. Compare against
            a slow but obviously-correct implementation on random input instead:

            ```python
            import random
            from bisect import bisect_left

            for _ in range(10_000):
                n = random.randint(0, 12)
                items = sorted(random.randint(0, 8) for _ in range(n))
                target = random.randint(0, 8)
                assert lower_bound(items, target) == bisect_left(items, target)
            ```

            Empty lists, duplicates, targets below the first element and above the last are all
            in there — for free, and without you having to think of them.

            ## Why it matters beyond arrays

            Binary search works on any monotone predicate, not just sorted arrays. "Smallest
            capacity that finishes the job in time", "earliest commit where the test fails" —
            `git bisect` is this algorithm, and so is every "search the answer" trick in
            competitive programming.

            | Operation | Linear scan | Binary search |
            | --- | --- | --- |
            | 1,000 items | 1,000 steps | 10 steps |
            | 1,000,000 items | 1,000,000 steps | 20 steps |
            | 10⁹ items | 10⁹ steps | 30 steps |

            Thirty comparisons to find one item among a billion. That is the whole reason to get
            the four lines right.
            '''
        ).strip(),
    },
    {
        "title": "Why does a spinning top not fall over?",
        "subtitle": "Angular momentum, torque and the precession that keeps a top upright.",
        "category": "Physics",
        "tags": ["mechanics", "angular-momentum", "intuition"],
        "content": textwrap.dedent(
            '''
            A stationary top falls over immediately. Spin it first and it stays up, leaning at an
            angle, its axis slowly sweeping a cone. Nothing about gravity changed. What changed is
            what gravity's torque now *does*.

            ## Torque changes angular momentum, not orientation

            For linear motion, force changes momentum:

            $$ \\vec{F} = \\frac{d\\vec{p}}{dt} $$

            Rotation has the exact analogue, with torque and angular momentum:

            $$ \\vec{\\tau} = \\frac{d\\vec{L}}{dt} $$

            That derivative is the whole answer. A torque does not tip an object over — it adds to
            the angular momentum *vector*. When \\(\\vec{L}\\) is zero, adding a sideways
            contribution starts a fall. When \\(\\vec{L}\\) is large and pointing along the spin
            axis, the same contribution mostly rotates \\(\\vec{L}\\) sideways instead.

            ## Where precession comes from

            Gravity pulls down at the centre of mass, a distance \\(r\\) from the pivot, giving a
            torque of magnitude \\(\\tau = mgr\\sin\\theta\\), directed **horizontally** —
            perpendicular to both gravity and the spin axis.

            A horizontal change to a nearly-horizontal-component angular momentum swings the axis
            around the vertical. That sweep is precession, at angular rate

            $$ \\Omega = \\frac{\\tau}{L\\sin\\theta} = \\frac{mgr}{I\\omega} $$

            Read the result: spin faster (larger \\(\\omega\\)) and precession slows down. That is
            the counter-intuitive part, and it is testable with a bicycle wheel.

            ## Checking it numerically

            The equations of motion are easier to trust once you have watched them run:

            ```python
            import numpy as np

            I, omega = 2.5e-4, 150.0     # kg m², rad/s
            m, g, r = 0.05, 9.81, 0.02   # kg, m/s², m

            Omega = m * g * r / (I * omega)
            print(f"precession: {Omega:.2f} rad/s = {Omega / (2 * np.pi):.2f} rev/s")

            # Axis direction over one precession period
            t = np.linspace(0, 2 * np.pi / Omega, 5)
            theta = np.deg2rad(20)
            axis = np.stack([
                np.sin(theta) * np.cos(Omega * t),
                np.sin(theta) * np.sin(Omega * t),
                np.full_like(t, np.cos(theta)),
            ])
            print(np.round(axis, 3))
            ```

            The z-component never changes: the lean angle holds while the axis walks around the
            vertical. That is exactly what a real top does.

            ## What friction does

            Nothing above dissipates energy, so the ideal top precesses forever. Real ones lose
            \\(\\omega\\) to friction, so \\(\\Omega = mgr / I\\omega\\) grows: the precession
            visibly speeds up as the top slows down, the lean angle opens out, and it falls. The
            frantic wobble at the end is the same equation, running out of angular momentum.

            > The useful habit here is reading \\(\\vec{\\tau} = d\\vec{L}/dt\\) as a statement
            > about directions, not magnitudes. Most rotational "paradoxes" — gyroscopes,
            > bicycle stability, the precession of the equinoxes — are that one sentence applied
            > carefully.
            '''
        ).strip(),
    },
    {
        "title": "Gradient descent, by hand",
        "subtitle": "One dataset, one loss function, and every derivative written out.",
        "category": "Machine Learning",
        "tags": ["optimisation", "calculus", "numpy"],
        "content": textwrap.dedent(
            '''
            Every neural network you have ever used is this algorithm, repeated. It is worth
            doing once with numbers small enough to check by hand.

            ## The setup

            Fit a line \\(\\hat{y} = wx + b\\) to some points by minimising mean squared error:

            $$ L(w, b) = \\frac{1}{n}\\sum_{i=1}^{n}\\left(wx_i + b - y_i\\right)^2 $$

            The gradient is two partial derivatives, each an average over the data:

            $$ \\frac{\\partial L}{\\partial w} = \\frac{2}{n}\\sum x_i (wx_i + b - y_i),
               \\qquad
               \\frac{\\partial L}{\\partial b} = \\frac{2}{n}\\sum (wx_i + b - y_i) $$

            ## Twelve lines of NumPy

            ```python
            import numpy as np

            x = np.array([1.0, 2.0, 3.0, 4.0])
            y = np.array([3.1, 4.9, 7.2, 8.8])       # roughly y = 2x + 1

            w, b, lr = 0.0, 0.0, 0.05

            for step in range(1, 201):
                error = w * x + b - y                 # residuals
                grad_w = 2 * np.mean(error * x)
                grad_b = 2 * np.mean(error)
                w -= lr * grad_w
                b -= lr * grad_b
                if step % 50 == 0:
                    print(f"step {step:3d}  loss {np.mean(error ** 2):.4f}  w {w:.3f}  b {b:.3f}")
            ```

            ```console
            step  50  loss 0.0356  w 2.010  b 0.906
            step 100  loss 0.0291  w 1.972  b 1.017
            step 150  loss 0.0290  w 1.966  b 1.036
            step 200  loss 0.0290  w 1.965  b 1.040
            ```

            It converges to \\(w \\approx 1.97, b \\approx 1.04\\) — the least-squares solution,
            found without ever solving a linear system.

            ## The learning rate is the whole game

            | Learning rate | What happens |
            | --- | --- |
            | 0.001 | Correct, but hundreds of times slower than it needs to be |
            | 0.05 | Smooth convergence |
            | 0.3 | Oscillates across the minimum, converges anyway |
            | 0.7 | Diverges to infinity in a dozen steps |

            There is a threshold — for quadratic losses, \\(2/\\lambda_{\\max}\\) of the Hessian —
            above which every step overshoots more than the last. Adaptive optimisers such as Adam
            are, at heart, per-parameter attempts to stay under it automatically.

            ## Check the gradient, always

            Analytic derivatives are where the bugs live. Compare against a finite difference:

            ```python
            def loss(w, b):
                return np.mean((w * x + b - y) ** 2)

            eps = 1e-6
            numeric = (loss(w + eps, b) - loss(w - eps, b)) / (2 * eps)
            analytic = 2 * np.mean((w * x + b - y) * x)
            assert abs(numeric - analytic) < 1e-6, (numeric, analytic)
            ```

            Two matching numbers is weak evidence; two matching numbers across random parameter
            values is strong evidence. Frameworks do this for you in their test suites — when you
            write a custom layer, you inherit the responsibility.

            !!! note "Scaling up"
                Batch gradient descent averages over the whole dataset. Stochastic gradient descent
                uses one sample, mini-batch SGD a few hundred. The noise is not a defect: it is
                what lets the optimiser escape the sharp minima that generalise badly.
            '''
        ).strip(),
    },
    {
        "title": "Your database is probably missing one index",
        "subtitle": "How to read a query plan, and what changes when the index exists.",
        "category": "Engineering",
        "tags": ["databases", "sql", "performance", "postgres"],
        "content": textwrap.dedent(
            '''
            Most "the app got slow" incidents are one missing index. Finding it takes about five
            minutes once you can read a query plan.

            ## Ask the database what it is doing

            Never guess. `EXPLAIN ANALYZE` runs the query and reports what actually happened:

            ```sql
            EXPLAIN ANALYZE
            SELECT id, title, published_at
            FROM blog_post
            WHERE status = 'published' AND published_at <= now()
            ORDER BY published_at DESC
            LIMIT 20;
            ```

            ```console
            Limit  (cost=18234.55..18234.60 rows=20 width=48) (actual time=412.883..412.891 rows=20 loops=1)
              ->  Sort  (cost=18234.55..18902.11 rows=267023 width=48) (actual time=412.881..412.884 rows=20)
                    Sort Key: published_at DESC
                    Sort Method: top-N heapsort  Memory: 27kB
                    ->  Seq Scan on blog_post  (cost=0.00..9873.29 rows=267023 width=48) (actual time=0.019..288.441 rows=266901)
                          Filter: ((status = 'published') AND (published_at <= now()))
                          Rows Removed by Filter: 33099
            Planning Time: 0.214 ms
            Execution Time: 412.944 ms
            ```

            Three phrases matter here:

            - **Seq Scan** — every row was read off disk.
            - **Rows Removed by Filter: 33099** — a third of that work was thrown away.
            - **Sort** — 267,000 rows sorted to return twenty.

            ## The fix

            Index the columns in the order the query uses them: equality filters first, then the
            ordering column.

            ```sql
            CREATE INDEX CONCURRENTLY idx_post_published
                ON blog_post (status, published_at DESC);
            ```

            ```console
            Limit  (cost=0.42..8.61 rows=20 width=48) (actual time=0.031..0.079 rows=20 loops=1)
              ->  Index Scan using idx_post_published on blog_post  (actual time=0.029..0.074 rows=20)
                    Index Cond: ((status = 'published') AND (published_at <= now()))
            Execution Time: 0.104 ms
            ```

            413 ms to 0.1 ms — four thousand times faster, no application code touched. The `Sort`
            node is gone entirely: the index is already in the right order.

            In Django, that index is one line on the model:

            ```python
            class Post(models.Model):
                class Meta:
                    indexes = [models.Index(fields=["status", "-published_at"])]
            ```

            ## Column order is not arbitrary

            A composite index on `(a, b)` serves `WHERE a = ?`, `WHERE a = ? AND b = ?` and
            `WHERE a = ? ORDER BY b` — but **not** `WHERE b = ?` alone. Equality columns first,
            then the range or sort column. Get the order wrong and the planner ignores the index
            you just paid for.

            ## What indexes cost

            They are not free:

            | Cost | Detail |
            | --- | --- |
            | Writes | Every `INSERT`/`UPDATE` maintains every index on the table |
            | Disk | Often 10–30% of the table size each |
            | Planning | Dozens of indexes slow down planning itself |

            So index the queries you actually run. `pg_stat_statements` ranks statements by total
            time; Django's `django-debug-toolbar` shows duplicated queries per page. Start at the
            top of those lists, not at the model definition.

            !!! note "Use CONCURRENTLY in production"
                A plain `CREATE INDEX` takes a lock that blocks writes for the duration.
                `CREATE INDEX CONCURRENTLY` does not — it is slower and cannot run inside a
                transaction, which is exactly the trade you want on a live table.
            '''
        ).strip(),
    },
    {
        "title": "Compound interest, and why intuition fails at it",
        "subtitle": "The arithmetic is trivial. Human estimates of it are not.",
        "category": "Economics",
        "tags": ["finance", "growth", "python"],
        "content": textwrap.dedent(
            '''
            Ask someone to estimate 7% growth over 30 years and most people guess two or three
            times the original. The answer is 7.6×. Exponential growth is the one piece of
            arithmetic where careful people are reliably wrong by a factor of three.

            ## The formula, and the rule of thumb

            $$ A = P\\left(1 + \\frac{r}{n}\\right)^{nt} $$

            with \\(P\\) the principal, \\(r\\) the annual rate, \\(n\\) compounding periods per
            year and \\(t\\) years. The useful shortcut is the **rule of 72**: money doubles in
            roughly \\(72 / r\\) years at \\(r\\) percent. At 7%, that is a touch over ten years —
            so three doublings in thirty, i.e. 8×. Close enough to 7.6 to do in your head.

            ```python
            def balance(principal, rate, years, periods_per_year=12):
                return principal * (1 + rate / periods_per_year) ** (periods_per_year * years)

            for years in (10, 20, 30, 40):
                print(f"{years:2d} years: {balance(1000, 0.07, years):>9,.0f}")
            ```

            ```console
            10 years:     2,010
            20 years:     4,038
            30 years:     8,116
            40 years:    16,313
            ```

            Each extra decade is worth more than every decade before it combined. That is the
            entire argument for starting early, and it is why fee differences that look trivial
            are not.

            ## Fees compound too

            A 1% annual fee does not cost you 1%. It costs you 1% of a compounding balance, every
            year, forever:

            ```python
            gross = balance(10_000, 0.07, 40)
            net = balance(10_000, 0.06, 40)      # same fund, 1% fee
            print(f"gross {gross:,.0f}  net {net:,.0f}  lost {1 - net / gross:.1%}")
            ```

            ```console
            gross 163,132  net 109,575  lost 32.8%
            ```

            One percent a year removed a third of the final balance. The fee is charged on the
            principal; what you lose is the compounding you never got.

            ## Real returns, not nominal

            Inflation compounds against you at the same time. The honest figure subtracts it
            *before* compounding, not after:

            $$ r_{\\text{real}} = \\frac{1 + r_{\\text{nominal}}}{1 + i} - 1 $$

            At 7% nominal and 3% inflation, the real rate is 3.88%, not 4%. Over forty years that
            gap is another 5% of the final balance — small annual differences, large terminal
            ones, which is the lesson in one sentence.

            > Whenever a percentage is quoted per year over many years, the arithmetic is
            > multiplicative and your intuition is additive. Reach for the rule of 72 before you
            > reach for an opinion.
            '''
        ).strip(),
    },
]


class Command(BaseCommand):
    help = "Create demo topics and example posts (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete the demo posts and topics before recreating them.",
        )
        parser.add_argument(
            "--author",
            default=None,
            help="Username to attribute the demo posts to. Defaults to the first superuser.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            slugs = [slugify(item["title"]) for item in POSTS]
            deleted, _ = Post.objects.filter(slug__in=slugs).delete()
            Category.objects.filter(
                slug__in=[slugify(item["name"]) for item in CATEGORIES], posts__isnull=True
            ).delete()
            self.stdout.write(f"Removed {deleted} demo object(s).")

        author = self._resolve_author(options["author"])

        for data in CATEGORIES:
            _, created = Category.objects.get_or_create(
                slug=slugify(data["name"]), defaults={**data}
            )
            if created:
                self.stdout.write(f"  + topic {data['name']}")

        for index, data in enumerate(POSTS):
            slug = slugify(data["title"])
            if Post.objects.filter(slug=slug).exists():
                self.stdout.write(f"  = post exists: {data['title']}")
                continue

            post = Post(
                title=data["title"],
                subtitle=data["subtitle"],
                slug=slug,
                author=author,
                category=Category.objects.filter(slug=slugify(data["category"])).first(),
                content=data["content"],
                status=Post.Status.PUBLISHED,
                is_featured=data.get("featured", False),
                published_at=timezone.now() - timezone.timedelta(days=index * 3),
            )
            post.save()
            post.tags.set(
                [
                    Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})[0]
                    for name in data["tags"]
                ]
            )
            self.stdout.write(f"  + post {post.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {Post.objects.published().count()} published post(s), "
                f"{Category.objects.count()} topic(s), author: {author.username}."
            )
        )

    def _resolve_author(self, username):
        if username:
            user = User.objects.filter(username=username).first()
            if user is None:
                raise SystemExit(f"No user named {username!r}.")
        else:
            user = User.objects.filter(is_superuser=True).order_by("pk").first()
            if user is None:
                user, _ = User.objects.get_or_create(
                    username="editor",
                    defaults={"email": "editor@example.com", "is_staff": True},
                )
                user.set_unusable_password()
                user.save()
                self.stdout.write(
                    self.style.WARNING(
                        "No superuser found — created the 'editor' account with no usable "
                        "password. Run `python manage.py createsuperuser` for a real login."
                    )
                )
        profile = user.profile
        if not profile.can_write or not profile.headline:
            profile.can_write = True
            profile.headline = profile.headline or "Writes about the details other explainers skip"
            profile.bio = profile.bio or (
                "Editor here. Interested in the point where a clean abstraction meets a messy "
                "detail — that is usually where the good explanation lives."
            )
            profile.save()
        return user
