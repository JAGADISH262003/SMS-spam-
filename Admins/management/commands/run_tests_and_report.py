import io
import re
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from Admins.models import TestRunReport # Corrected import path

class Command(BaseCommand):
    help = 'Runs tests for User, Admins, and Backend apps and saves the report to the database.'

    def handle(self, *args, **options):
        self.stdout.write("Starting test execution...")

        # Using StringIO to capture test output
        # Redirecting sys.stdout and sys.stderr for more reliable capture
        import sys
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = output_buffer = io.StringIO()
        sys.stderr = error_buffer = io.StringIO()

        try:
            call_command('test', 'User', 'Admins', 'Backend', verbosity=1)
        except SystemExit as e:
            self.stdout.write(f"Test runner exited with code: {e.code}") # Write to original stdout via self.stdout
        except Exception as e:
            # Restore stdout/stderr before writing error to them
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.stderr.write(self.style.ERROR(f"Exception during test execution: {str(e)}"))
            # Capture any buffered output before restoring
            full_output_on_exc = output_buffer.getvalue() + "\n--- Errors (if any) ---\n" + error_buffer.getvalue() + f"\nCOMMAND EXCEPTION: {str(e)}"
            report = TestRunReport(
                run_at=timezone.now(),
                report_output=full_output_on_exc,
                was_successful=False,
                total_tests=-1
            )
            report.save()
            self.stderr.write(self.style.ERROR("Test execution failed catastrophically. Report saved with error state."))
            return
        finally:
            # Ensure original stdout/stderr are restored
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        full_output = output_buffer.getvalue() + "\n--- Captured Stderr ---\n" + error_buffer.getvalue()
        output_buffer.close()
        error_buffer.close()

        # Write to original stdout now that it's restored
        self.stdout.write("Test execution finished. Parsing results...")

        # Initialize counters
        total_tests = 0
        failed_tests = 0
        errors = 0
        skipped_tests = 0
        passed_tests = 0 # Initialize passed_tests

        # Default overall success to False, prove it True
        final_report_successful_status = False

        # Regex patterns to find test summary details
        # Example: "Ran 17 tests in 0.123s"
        ran_match = re.search(r"Ran (\d+) tests? in", full_output)
        if ran_match:
            total_tests = int(ran_match.group(1))

        # Example: "OK (skipped=1)" or "OK" - Remove $ to allow trailing text
        ok_match = re.search(r"^OK(?: \(skipped=(\d+)\))?", full_output, re.MULTILINE)
        # Example: "FAILED (failures=1, errors=0, skipped=1)" - Remove $
        failed_match = re.search(r"^FAILED \(failures=(\d+)(?:, errors=(\d+))?(?:, skipped=(\d+))?\)", full_output, re.MULTILINE)

        if ok_match:
            final_report_successful_status = True # OK means no failures or errors
            if ok_match.group(1): # This is the skipped group
                skipped_tests = int(ok_match.group(1))
        elif failed_match:
            final_report_successful_status = False # FAILED explicitly means not successful
            failed_tests = int(failed_match.group(1) or 0) # Group 1 is failures
            errors = int(failed_match.group(2) or 0)       # Group 2 is errors
            skipped_tests = int(failed_match.group(3) or 0)# Group 3 is skipped
        else:
            # If no clear OK or FAILED summary, and some tests ran.
            # This state is ambiguous. It might happen if verbosity changes output format.
            # Or if test runner crashed before summary but after "Ran X tests".
            self.stderr.write(self.style.WARNING("Could not parse test summary (OK/FAILED line not found). Report marked as unsuccessful."))
            final_report_successful_status = False
            # Try to find individual test failure lines if summary is missing
            if "FAIL:" in full_output and failed_tests == 0 and errors == 0: # Basic check
                 errors = -1 # Indicate parsing issue for detailed errors

        # Calculate passed if total_tests is known and we have other counts
        if total_tests > 0 :
            passed_tests = total_tests - failed_tests - errors - skipped_tests
            if passed_tests < 0: # Should not happen with correct parsing from FAILED line
                 # This might happen if only "Ran X tests" was found and no OK/FAILED line
                 passed_tests = 0 # Avoid negative
                 # If OK/FAILED line was missing, and passed is now 0, it's likely an error state
                 if not ok_match and not failed_match:
                     final_report_successful_status = False
        elif total_tests == 0 and "Ran 0 tests" in full_output:
             # If "Ran 0 tests" is in output and no "OK" or "FAILED" line, it's usually an OK run.
             if not ok_match and not failed_match:
                 final_report_successful_status = True


        report = TestRunReport(
            run_at=timezone.now(), # Use timezone.now() for consistency
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            errors=errors,
            report_output=full_output,
            was_successful=final_report_successful_status
        )
        report.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully ran tests and saved report. ID: {report.id}"))
        self.stdout.write(f"Summary: Total={total_tests}, Passed={passed_tests}, Failed={failed_tests}, Errors={errors}, Skipped={skipped_tests}")
        if not final_report_successful_status:
            self.stderr.write(self.style.ERROR("Test run reported failures or errors, or could not be fully parsed."))
