# A Bluffer's Guide to USS Conditional Indexation

<!-- ================================================================
     AUTHORING INSTRUCTIONS
     - Your text: plain paragraphs — rendered as bjp() callout boxes.
     - Generated scaffold text: inside ```claude blocks — rendered as st.markdown.
     - Charts: inside ```chart blocks — rendered automatically.
     - Section headings: ## ... → st.subheader
     - Run `uv run python build_page.py` to regenerate pages/2_Bluffers_Guide.py.
     ================================================================ -->
I am a bluffer on this and I'm guessing you are too. I hope to help you become a better bluffer.

I am pensions layperson who is slowly autodidacting my way to what I hope is being a highly sophisticated layperson. I have served on HEC for a while and for the last two years on the USS Advisory Committee which mostly reviews appeal cases. As such, I've been on UCU's superannuation working group (SWG) for the past two years. I have not been a negotiator but I have met with them (a lot...SWG has a lot of meetings) and participated in a lot negotiation discussions. 

I have wanted to build some models to help inform discussions. These models I have right now are super duper preliminary and, at best, can inform lay discussions. They are not suitable for either:

1. Driving negotiations (we pay professional actuaries to do those)
2. Personal financial advice; THIS IS NOT A PENSION PLANNING TOOL!!

Do NOT think this will help you plan your own pension. If you use this in any way for your own pension planning you do so at your own, rather foolish, risk. Always consult with a professional advisor who has access to your details.

UCU provides one free initial financial consultation with [Quilter Financial Advisors](https://www.ucu.org.uk/quilterfinancialadvice). Using that is a million times better than in ANY way thinking you're getting good financial advice or savvy from this site.

For financial advice for most people, you will need to pay someone something.

One thing I've seen on the USS Advisory Committee are cases where people thought USS provide information was somehow formal financial advice *or* a binding contract. It's almost certainly neither. Anything I write her or you derive from this thing is 10000% not either.

Book the free appointment. First one is free so you can get your feet wet safely.

## A couple more caveats

This is an early version of the tutorial and the models underlying it. I THINK they will be helpful, but YMMV. Working through these models has been illuminating for me.  [JG comment: from here to end of para I was confused if you were talking about current scheme as soft-cap DB or CI I wondered about deleting these few sentences or rephrasing as i think mentioning the vauluation methodology is important] On the one hand, with the right valuation methodology, we could easily go back to full indexation (on an affordability basis). However, we might not get that methodology. The soft cap is probably suboptimal in a number of ways but I thought more CI designs were much worse. At least against the past 10 years or so, the soft cap and even a fairly hostle CI regime under a fairly prudent valuation methodology are pretty close.

CI potentially allows for "automagical" benefit improvement thus insulating us from having to negotiate every benefit enhancement and put it up against contribution reduction. Every negotiation is a risk with an adversary. Since the swing vote (the "independent") chair [of USS JNC] has historically not been super awesome for us, we need to consider that risk seriously.

What this tool does not (yet) explore is how CI can support changes in investment strategy to a more pro-growth position. A better valuation supports that too, but CI contributes as well.

Anyway, YMMV!

---

## Money Flows

### Inflows/Assets

You (and nominally your employer, but employer contributions are part of your compensation so it's really all you!) pay money into USS. Eventually you hope to get money out. But you don't have an individual account with USS that your money goes into. It's not a fancy ISA.

There are two sources of cash: member contributions and returns on the pooled investment fund. The scheme is "open to new members" which means new members (lots of them) get enrolled in the scheme and will do so for the forseeable future. If USS "closed to new accrual", that is, stopped taking any new contributions, the contributions immediately drop to 0. If USS "closed to new members", that is, stopped enrolling new members, then eventually all current members would retire and contributions would go to 0. Critically, we would have to pay everyone's pension out. If the return on assets didn't match the monthly outgoings then we'd start dipping into capital at that point. A closed scheme is like an individual ISA: you pay in (make contributions) as long as you're working, but when you retire your guaranteed pension draws on the interest and perhaps the capital if needed. If you run out...sucks to be you. If USS closed and ran out of money before all the pensioners died, employers would be the backstop and after that the Pension Protection Fund.

But for an open scheme, the contributors (as a group) never collectively retire.

### Outflows/Liabilities

USS pays out pensions. It has to pay out your lump sum and then your pension until you and your beneficiaries die. In a pure pay-as-you-go scheme (like government pensions), the outflows come directly from the inflows (i.e., from current taxes, a form of contribution). Critically, governments can borrow and they can change the law so as to change (or halt) benefits. For fund-based schemes, accural (the pension you've earned an entitlement to over the years) is a *contractual promise*. Once you've accrued a benefit, USS is ordinarily required to cover it. Future accural is up in the air, always [JG and for USS this is decied by the JNC]. After all, the scheme could close. In some hypothetical variants that would stop all contributions *and* future accural.

Now, obviously, USS is not paying out to all members now, so some promises are only about the future. If you die before retiring, your cost to the scheme drops from lump sum plus (let's say) 20 years of pension payments to just the lump sum [I'm not sure this is correct isn't it 3 x annual salary for DIS]. But until a member exits [JG do you mean dies?] USS, USS owes them something.

Of course, USS doesn't know what it owes you for the duration of your retirement because what it will have paid you isn't determined until you die. If you drop dead with only 10 years accrual [JG do you mean with only 10 years of drawing benefits?], your benefits are small and thus so is USS's actual liability wrt to you. If you rise to a highly paid dean in your 20s, accure for 40 years and then live another 30 and are survived by your spouse for another 10...it costs a lot to fund all that. Any random individual member could be one of these extremes, though most are not. (The magic of actutorial analysis let's us make pretty good predictions at the population level.)

Thus when the JNC decides what promises to make [JG: techincally JNC decides what promises to make, USS costs them], USS has to predict what those promises will cost and what their income will be. These need to balance in the long run. Indeed, in the medium run! They publish their predicted cashflows here under Documents https://www.uss.co.uk/news-and-views/briefings-and-analysis

---

## The Upshot

USS 

1. collects contributions, invests them, and pays pension out of the returns (mostly) [JG do you know this? I would need to check, over the last few years with 3 year anualised at -6% I dont think this is true];
2. has an obligation to pay out all the pensions obligations it has accrued and revalue or index them each year;
3. doesn't know exactly what those obligations are because they depend on what happens in the future;
4. doesn't know what the future contributions and returns will be because prediction is hard, *especially** about the future.

Thus USS must make a rationally grounded, restricted by regulation *best guess* as to what its future costs and income will be and whether they balance over a give horizon.

---

## Indexation and USS's current approach

Imagine you had accrued a USS pension of £1000 (a month, a year...doesn't really matter) in 2017 when you retired. Suppose this met your needs and even allowed for a bit of leisure spending. What happens to your purchasing power by 2024?
    
```chart
type = real_pension_path
toggleable = true 
schemes = full_cpi,  none
start_year = 2017
pension = 1000
caption = Figure 1. Starting pension: £1,000/month in 2017. With the "show nominal" toggle *off*, the chart is in constant pounds. Thus the *value* of your pension is the declining line. If you toggle nominal *on*, the the pension stays at £1000 (a flat lines) and the rising lines show how many pounds you'd need to maintain purchasing power.
```
As we can see, your purchasing power is reduced to £766. Your pension is the same in "nominal" pounds. The deposit you get was £1000 then and it's £1000 now. But the *real value* of that £1000 has fallen. It is now as if you had received a pension of £766 (a loss of 23.4%).

This (to a first approximation) does not violate any promises by USS...it promised you a £1000/month pension and you have one! 

This is where indexation comes in. 

By law, pensions must be increased by CPI or 2.5%, whichever is less. Before 2016 [JG I think it was 2011], USS had *full* indexation. That is, your *nominal* pension rose by the full CPI percentage which means your *purchasing power* stayed the same (if CPI is a good match for your spending). You pension supports the lifestyle to which you are accustomed to over your full lifetime.

(Note: USS usually uses the CPI inflation metric. In other contexts, UCU uses the RPI metric which tends to indicate higher inflation. Which measure to use has not been a central negotiating point. I'll try to use "CPI" instead of "inflation" from here on as it's more precise.) 

However, because of valuation issues (which we're going to dive into) from 2010, USS ended full indexation in 2016 [again I think 2011] and replaced it with the so called *soft cap*. The soft cap matches CPI up to 5%, then matches *half* of CPI from 5%-15%. Thus the maximum indexation is 10% when CPI reaches 15%.

Thus under current USS indexation, if CPI is less than 5%, you're good. From 5%-15%...you lose some and above 15%…you're on your own. 

However, even with recent high inflation, the soft cap got close to full indexation. Going from £1000 purchasing power to £967 is a clear loss (and that loss adds up over time!), it is substantially better than the statutory minimum of £887 [is this if 2.5% is applied - perhaps say so].

One thing to remember is that losses compound. Subsequent indexation is on top of your *nominal* pension. Suppose in a year inflation is above indexation and the effect is that your real pension is £950/month. That adds up to a loss of £600 over the year. But now imagine that next year we have full indexation *for that year*. You still have only £950/month of purchasing power! Normal indexation is not retrospective and, currently, would require a negotiated augmentation of benefits to "catch you up".


```chart
type = real_pension_path
schemes = full_cpi, soft_cap, statutory, none
toggleable = true 
start_year = 2017
pension = 1000
caption = Figure 2. Real monthly pension (2017 prices) under full CPI indexation, the USS soft cap, statutory minimum (2.5% cap), and no indexation at all. This uses historical CPI rates. Starting pension: £1,000/month. Again, the nominal switch shows you what you would need in today's pounds to maintain purchasing power. With it off it shows you the loss of purchasing power from 2017.
```


---

## The funding ratio: can the scheme afford it?

Clearly, indexation, indeed, full indexation, should be the strong default. For UK state pensions, we have the "[triple lock](https://www.bbc.co.uk/news/articles/cq6m03ld7nvo)": state pensions will rise by 2.5%, the average wage increase, or by CPI whichever is *highest*. This means that not only will the state pension not *lose* value, but it could *increase* in real value (determined by CPI). Of course, the actual value of UK pensions is both relatively tiny and is hard to get.

![](http://researchbriefings.files.parliament.uk/documents/SN00290/assets/19c8f26d-8008-432a-a93f-0d1a1587803e.png)

From the House of Commons [research report on pensions](https://commonslibrary.parliament.uk/research-briefings/sn00290/), "The UK has an overall net replacement rate of 54.4% from mandatory pensions for an average earner, below the OECD average of 61.4%."

Furthermore, the triple lock keeps getting hit by complaints that it's too expensive. It, of course, is funded out of taxes and borrowing. For USS, pensions are funded out of contributions and returns. There is of course, uncertainty about both. [JG I suggested softening a bit]

Thus, every 3 years USS undergoes a "valuation": An exercise to determine what it believes its likely future liabilities and assets will be over a long time horizon.

Again, these are predictions. About the future. Indeed, about the far future. (10-50 years mostly, not millennia). But once a prediction is made, USS has to act on it.

The key magic number is the "funding ratio" (FR), that is the ratio of (projected) assets to (projected) liabilities. These are both sensitive to a number of assumptions and guided by your tolerance of risk (which is partly controlled by the pension regulator). Historically, the USS valuation methodology has been hugely *pessimistic* about the future. (This is what is meant by saying it is "excessively prudent"). Consider the old USS funding ratio estimate over time

```chart
type = fr_history
bases = uss_tp
highlight = uss_tp
show_cpi = false
caption = Figure 3. USS estimated funding ratio 2008–2025, with annual CPI shown as bars. The scheme has been in technical deficit on the USS TP basis for most of 2009–2022.
```
If the FR is below 100%, then USS formally believes that they will not be able to meet their obligations with the contributions and investments they currently have, much less fund indexation. Remember that they *have* to index up to 2.5% [no - I don't think the triple lock doesn't apply to USS, if CPI is 0, indexation is 0].

Thus, USS must figure out what to do they could:

1. cut future benefits (not accrued benefits!)
2. increase contributions
3. both!
4. something sensible that UCU forces on them

As you might expect, 3 is the default approach of USS. Hence the move from full indexation to the soft cap. Also the proposal to introduce a hard-cap of 2.5% in 2022. The soft cap reduces future liability *across a range of possibilities.* Instead of having to accomodate futures with years of 15% indexation, the max will be 10%. For the proposed hard-cap the maximum was 2.5% "Unaffordable" contribution rises triggered many attempts to slash benefits including the attempted conversion to defined contribution.

It is striking that from 2009 to 2021, the USS estimate was that they were underwater and consistently so. UCU argued that there was something deeply wrong with their methodology. This became undeniable when their valuation swung from billions in deficit to billions in surplus after a pointless benefit cut. The world did not change as much as their valuation results did. That suggested something deeply wrong with their valuation methodology. It's one thing to be consistently depressed, but another to have wild swings on a relatively steady economic outlook.

UCU tackled this and commissioned the development of an alternative approach to valuation. Unlike, the Doom and Gloom USS approach, it was centered on the idea of "best estimate". Instead of being all chicken little about the future, the UCU approach aims to be as *accurate* as reasonably possible. This fundamental difference in perspectives yields fundamentally different results. Our team also developed a "prudent" version of our methodology, which basically starts from a best estimate and then adds a *bit* of gloom. Not wild doom. Just enough gloom to be support a bit of risk aversion.

Unsurprisingly, these estimates support a >100% FR since 2017 [JG do we have a public source for this, or do you mean the best-estimates]. Not that alone doesn't mean that the estimates are good. After all, maybe they are unduly optimistic!

However, unlike the USS methodology, they don't (in the historical data) show the bizarre swings from deficit to surplus (or the reverse). They still *fluctuate* so demonstrate sensitivity to current economic measures. But they aren't obviously *detached* from the economy.


```chart
type = fr_history
bases = uss_tp, ucu_prudent, ucu_best_est
highlight = ucu_best_est
show_cpi = false
caption = Figure 4. USS estimated funding ratio 2008–2025 on three valuation bases. The scheme has been in technical deficit on the USS TP basis for most of 2009–2022. The UCU Best Estimates valuation averages 30%-33% better than the prudent valuation.
```

Even with the prudent version, our methodology does not support a deficit driven crisis. The fact that our approach to valuation does not have a persistent indifference to the actual economy or  massive odd swings where the USS approach does gives us some confidence that UCU's isn't just optimistic symmetrically with the pessimisms of the USS approach. We believe (for lots of reasons) that the USS approach was broken. It going from a massive deficit to a massive surplus with no real economic justification indicates that their approach was far too sensitive to some inputs.

Of course, Even if the funding ratio is above 100%, CPI could be large enough and the surplus small enough that full indexation might require additional contributions (on that valuation). 

Consider, the cost of CPI indexation

```chart
  type = fr_affordability
  bases = uss_tp, ucu_prudent, ucu_best_est
  schemes = full_cpi
  show_cpi = true
  caption = Figure 5. The "full CPI" line indicates the FR needed in order to afford full indexation. If the full CPI line is *below* a valuation line, then it is affordable according to that valuation without additional funding or benefit cuts.  Note that this is a very simplifed point to point estimate thus does not include compounding due to indexation or surplus accumulation.
```

(Note that the bars are interpreted against the right axis. It's a little confusing but it gives you a feel for what CPI is in each year which drives the cost of full CPI indexation line. They should track.)

The way to think about the cost line is that it is the amount of surplus *above* full funding of unindexed liabilities needed to break even with full CPI indexation. Thus, if your FR is below 100%, this indicates how much *more* below 100% you'd be if you did full indexation. If your valuation is *above* the cost line, then you can afford indexation with no other changes. Indeed, if the valuation is well above the indexation cost line, that indicates further surplus that could be used to improve benefits or reduce costs.

This chart illustrates just how overwhelming the valuation methodology is in determining what happens to our pensions. This is before we consider the effects of these predictions on investment strategy. The cost of a clearly bonkers methodology has been degradation of our pensions and massive industrial action to try to mitigate it.

Fixing the valuation is job 1 and what UCU has been focused on in negotiations for the past several years. And we've made a lot of progress! We'll see what happens this year, but we've gotten a basic agreement to move toward a methodology more along our lines. We'll see what happen in 2026-2027!

---


## What is conditional indexation?

We've seen "match CPI" indexation and "match CPI until you don't" (soft cap) indexation. These are *unconditional* forms of indexation. They are intended to happen without regard to affordability.

Of course, they are not *truly* unconditional in the sense that affordability (or *perceived* affordability) can and has triggered contribution and benefit changes. The move from full CPI to the soft cap is itself an indicator of the conditionality of any indexation. However, such changes tend to be big, slow, crude, and disruptive. Unwinding them is a big, difficult deal. We have recent experience of this with the roll out then roll back of big benefit cuts in the light of the COVID valuation. The amount of effort and expense to USS to "restore" benefits was enormous, and that is dwarfed by the lost pay and pain of the industrial action needed to get us back what *by USS's own methodology* should have never been lost.

What is called conditional indexation attempts to make the gross conditionality of indexation on funding ratio more flexible, nimble, and, one hopes, less damaging. The basic idea is to make any given annual indexation conditional on (and estimate of) the current funding raito. If full indexation is affordable at that moment, give it. If not, then don't down to some floor. If that floor is 0%, then in a bad investment, high inflation year, we might receive no indexation at all.

However, one intuition is that the combination of high inflation and low returns is unlikely in a modern, reasonably run economy. Thus most CI schemes include a "catch up" mechanism. If after a sub-inflation indexation, we have a surplus over what's need to cover current inflation, we back fill the low indexation years. 

If we zoom in on the affordability chart from 2019-2025:

```chart
  type = fr_affordability
  bases = ucu_prudent
  schemes = full_cpi
  start_year = 2019
  show_cpi = true
  caption = Figure 6. We're focusing on a period where full CPI indexation has years of unaffordability (2021-2023) according to an OK methodology and years where, according that methodology, we have a post indexation surplus.
```
From 2021-2024, the cost line is above the valuation line, thus indicating that full CPI is "not affordable".  Note that in 2022 and 2023, inflation is above the soft cap (which tops out at 7.5% CPI).

However, in 2024 and 2025 things improve significantly. Returns are up, inflation is down, but even thought backfilling seems like it should be affordable, we would have to *change the scheme* via negotiation to get full indexation for those two years (assuming no cuts happened). With most conditional indexation years, surplus of indexation in 2023-2024 would be used to "fix" the lost of real value experienced in 2021-2022.

2021 is interesting because the valuation estimate goes below 100% FR and thus the scheme is in technical deficit even before indication. If the CI scheme include 0% indexation then there would be no indexation that year though it seems it would get included in the catch up in 2024.

One thing that is crystal clear: the valuation matters so very much:

```chart
  type = fr_affordability
  bases = uss_tp
  schemes = full_cpi
  start_year = 2019
  show_cpi = true
  caption = Figure 7. Same as figure 6 but with the USS old skool valuation methodlogy.
```

Interestingly, with many CI schemes, some effects of the horrid methodology can be mitigated. As the FR improves, the surplus could be semi-automatically used to pay back lost indexation. Instead of having to argue *de novo* that surplus should go back to members, many CI schemes will just do that by default.

Moreover, there's no reason a CI scheme need to include a 0% lower bound or an inflation measure upper bound. The CI floor could be the soft cap, which is a strict improvement over the current situation. The CI target could be RPI+2.5% which would target a gradually *improving* pension in real terms.

Super-inflation indexation is a simple benefit enhancement that evenly applies to  both active and retired members. It thus doesn't rectify existing disparities (e.g., new members won't have final salary and probably have less generous accural rates than at least some retired members). Accrual and contribution rates do need ongoing negotiations but stabilising the valuation makes it less likely that we need pit active members against retired members. By allowing a little slack in the system, we can share some of the burden and some of the benefits in a uniform way.

Equally, one could easily design a hostile CI scheme (e.g., include 0%, no or limited catch up). Similarly, one could misuse positive valuations to cut contributions for employers (a stealth pay cut). We should not agree to any of these, obviously!

Also, if like the classic USS methodology, we have a long bout of technical deficit, we risk a comparably long bout of no or low indexation.

## How would CI have performed historically?

Ok, this is fine, but what would have been the actual affect on our pensions given recent inflation?

Let's consider 4 indexation schemes: 
1. two unconditional: 
    * full CPI (the best!) and
    * the soft cap (what we have), vs.
2. two conditional: 
    * one with a 0% floor (what the employers likely would prefer)
    * and one with a soft cap floor (that is, the conditionality is all above the soft cap; this will track the soft cap until we go above 5% CPI in which case soft-cap+CI scheme *could* improve on the soft cap (depening on the FR)).
    

```chart
type = ci_replay
schemes = full_cpi, soft_cap, proportional, hybrid
basis = ucu_prudent
start_year = 2016
pension = 1000
caption = Figure 8. Simulated real value pension under various indexation schemes from 2017-2025 against historical data.
```

Obviously, full CPI is best, but the soft cap fares worse by 2025 than either CI scheme. However, it does better than 0%+ CI in three years. Soft-cap+ CI stays the same as the soft-cap until 2023, where catch up kicks into start recovering value.

Thus the soft cap gives us a *permanent* reduction in indexation. That will get worse over time as future indexation will start from this lower real baseline. 0%+ CI does dip lower than the others, but recovered quickly. Softcap+ is the best for members after full CPI indexation, but recall the actual fundable indexation is 0+CI. So there is, potentially, a funding gap in there which must be recovered from somewhere.

If we look at the 10 year accumulation of pension, we find them remarkably close:

```chart                                                                      
  type = ci_replay_cumulative                                                 
  schemes = full_cpi, soft_cap, proportional, hybrid                            
  basis = ucu_prudent
  start_year = 2016                                                             
  pension = 1000                                                                
  caption = Total real pension received 2016–2025 per scheme, UCU Prudent basis.
   Starting pension £1,000/yr. 
```

The soft cap wins out over 0%+ by £2 over 10 years, but will potentially lag more and more over time. The damage of the soft cap remains and compounds.

This illustrates the "automatic stabilisation" potential of CI. Catch up means the scheme catches up. Right now, with the soft cap, we have to *negotiate* a catch up even though the scheme can afford a catch up.

---

## Second order effects

CI does not mean we never need to make adjustments to benefits or contributions rates. We could accumulate ever greater surpluses. We could have persistently low returns and high inflation. Something weird could happen. A CI scheme can provide some degree of cross year balancing, but it'll have limits. If things suck hard enough for long enough, we're gonna have issues.

Different CI schemes might (MIGHT) embolden USS fund managers to be less conservative in their investments. Maybe. They seem to think so. Personally, I think the UCU valuationtion and most critically the *mindset* in entails is way more significant. 

If a CI scheme makes USS more stable, then that's good. Personally, I think less negotiation is *good* for members because 1) there's a lot of costs at having to constant fight battles and 2) there are more chances for shenanigans. Pensions should be more boring than we've experienced.

The fact that our pay has been eroded by inflation means having a better pension is even more important. Lower pay means a lower baseline for your pension and thus less headroom for further erosion.

---

## A stealth defined contribution plan?

There is definitely some "transfer of risk" though I think it's not *quite* only from employers to members. It's also from active members to retired members and from newer members to those more advanced in the scheme. Prioritized (not "guarunteed") indexation means that deficits need to get covered by changes to contributions, accural, or both. In a world where pay grew with inflation and job continuity and security were higher that might be the right way to share risk. But in a full indexation schem with high inflation and non-inflation matching pay risees, it is the active members, not the retired, that will feel like they are on a "fixed income".

More fundamentally, DC plans put *all* the risk on members and on members individually. Your ISA fund *is* your retirement fund. You need to manage it and you generally don't get to top it up after you retired. If you retired during a downturn, you might end up eroding yoru captial. You might get scammed out of the whole thing.

Even with 0+ CI, these risks are mitigated or nigh eliminated. This is really quite different that a DC plan. 

