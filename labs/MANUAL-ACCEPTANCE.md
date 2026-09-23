# Checks that cannot be completed by a simulated browser

Record device model, OS, browser, screen-reader version, date and actual observations. Leave unexecuted rows marked NOT RUN. A desktop WebKit result is not an iPhone result.

| Task | Expected observation | Actual observation / status |
| --- | --- | --- |
| Open the reading index on the actual phone | Title, chapter names and links readable without horizontal page scrolling | NOT RUN |
| Enlarge text / zoom | Content remains available, focused controls stay visible | NOT RUN |
| Navigate headings with VoiceOver/TalkBack | Headings describe the content in a sensible hierarchy | NOT RUN |
| Traverse navigation links | Link names identify their destination without surrounding prose | NOT RUN |
| Read a code example | Code can be reached and understood; long lines scroll within the block | NOT RUN |
| Read a comparison table | Headers and data relationships are understandable | NOT RUN |
| Open and return from a chapter | Focus and reading position are predictable | NOT RUN |
| Use external keyboard, if supported | All controls reachable; no trap; focus visible | NOT RUN |
| Sign in to the actual lab | Labels, validation errors and success state are announced | NOT RUN |
| Submit an empty / invalid form | Error is associated with the input and not conveyed by colour alone | NOT RUN |
| Stream an answer | Updates do not repeatedly interrupt reading; final state understandable | NOT RUN |
| Disconnect / reconnect network | Error and recovery state are perceivable; no duplicate submissions | NOT RUN |
| Log out during a live stream | Access stops and signed-out state is announced | NOT RUN |
| Background app then return | Expiry/reconnect state is accurate; stale content is labelled | NOT RUN |

Record failures as: task, reproduction steps, observed announcement/behavior, expected behavior, affected device and retest result. Fix the underlying semantic HTML or state announcement, then retest on the same assistive technology. Automated accessibility reports remain useful but do not fill these rows.

## Unaided interview round

Without reading the answer key, spend twelve minutes answering: “An order commits, the response is lost, and two clients retry concurrently. Design a Java/Python API, database constraint and idempotency contract that prevents duplicate orders. Explain payload conflicts, retries after crashes, an outbox event and what Kafka does not guarantee about external payments. Give four tests.”

Submit your original answer and elapsed time. Score out of twenty: five points for a correct durable idempotency contract; four for concurrency and transaction boundaries; four for crash/retry reasoning; four for meaningful tests; three for clear tradeoffs. A passing practice score is sixteen, with no duplicate-payment safety error. No score has been assigned yet. The tutor should identify misconceptions, give a different follow-up problem and grade another unaided attempt; memorizing this answer is insufficient.
