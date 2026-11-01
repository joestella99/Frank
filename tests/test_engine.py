import unittest
from job_engine import rank,collect_board
from cloud_hunt import merge

class FrankTests(unittest.TestCase):
    def test_sports_nyc_good(self):
        score,why=rank(dict(title="Software Engineer",location="New York, NY",sports=True,description="Python SQL API"))
        self.assertGreaterEqual(score,85)
        self.assertIn("Sports technology",why)
    def test_bad_fit(self):
        self.assertEqual(rank(dict(title="Account Executive",location="New York"))[0],0)
        self.assertEqual(rank(dict(title="Software Engineer",location="London, UK"))[0],0)
    def test_remote_cautious(self):
        self.assertIn("verify",rank(dict(title="Product Manager",location="Remote"))[1])
    def test_ashby_api(self):
        b=dict(provider="ashby",slug="demo",name="Demo",sports=True)
        def fake(url):return {"jobs":[dict(id="a",title="Product Manager",location="New York",jobUrl="https://example.com/job")]}
        self.assertEqual(collect_board(b,fake)[0]["id"],"ashby:demo:a")
    def test_dedup(self):
        j=dict(id="ashby:demo:1",title="Software Engineer",location="NYC",company="Demo",
               sports=True,description="",url="https://example.com/job",source="ashby",board="ashby:demo",posted_at="")
        jobs,new=merge([],[j],{"ashby:demo"},"2026-11-01T19:00:00+00:00")
        self.assertEqual(len(new),1)
        _,new2=merge(jobs,[j],{"ashby:demo"},"2026-11-01T19:00:00+00:00")
        self.assertEqual(len(new2),0)
if __name__=="__main__":unittest.main()
